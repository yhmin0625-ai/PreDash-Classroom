import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from predash.alerts import market_status, transition, concentration, month_end_check


class MarketAlerts(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 16, 18, tzinfo=ZoneInfo('Asia/Seoul'))
        self.vix = {'close': 18, 'date': '2026-10-15'}
        self.market = {'fetched': self.now.isoformat(), 'lamps': {
            name: {'close': 130, 'ma10': 120, 'ma20': 110, 'date': '2026-10-16'}
            for name in ('코스피', '코스닥')}}

    def signal(self):
        return market_status(self.vix, self.market, self.now)

    def test_vix_boundaries(self):
        for value, level in ((14.99,1),(15,2),(19.99,2),(20,3),(29.99,3),(30,4)):
            self.vix['close']=value
            self.assertEqual(self.signal()['level'],level)

    def test_highest_input_wins(self):
        self.vix['close']=14
        self.market['lamps']['코스닥']['close']=80
        self.assertEqual(self.signal()['level'],3)
        self.vix['close']=32
        self.assertEqual(self.signal()['level'],4)

    def test_ma_equality_and_between_are_caution(self):
        self.vix['close']=14
        for price in (110,115,120):
            self.market['lamps']['코스피']['close']=price
            self.assertEqual(self.signal()['level'],2)

    def test_missing_low_data_is_unknown(self):
        for missing in ('코스피','코스닥'):
            market=deepcopy(self.market);del market['lamps'][missing]
            self.assertEqual(market_status(self.vix,market,self.now)['state'],'unknown')
        self.assertEqual(market_status(None,self.market,self.now)['state'],'unknown')

    def test_partial_risk_is_visible(self):
        signal=market_status({'close':35,'date':'2026-10-15'},None,self.now)
        self.assertEqual(signal['level'],4)
        self.assertIn('최소',signal['label'])
        self.assertFalse(signal['complete'])

    def test_invalid_stale_future(self):
        for value in (float('nan'),float('inf'),-1,True,None):
            self.assertEqual(market_status({'close':value,'date':'2026-10-15'},self.market,self.now)['state'],'unknown')
        for day in ('2026-10-01','2026-10-17'):
            self.assertEqual(market_status({'close':18,'date':day},self.market,self.now)['state'],'unknown')
        self.market['fetched']=(self.now-timedelta(days=2)).isoformat()
        self.assertEqual(self.signal()['state'],'unknown')

    def test_mismatched_dates_and_cached_label(self):
        self.market['lamps']['코스닥']['date']='2026-10-15'
        self.assertEqual(self.signal()['state'],'unknown')
        self.market['lamps']['코스피'].update(state='상승',close=80)
        self.assertEqual(self.signal()['level'],3)

    def test_caution_no_popup_then_alert_then_risk(self):
        memory,event=transition(None,self.signal(),self.now)
        self.assertIsNone(event)
        for value,kind in ((22,'alert'),(32,'risk')):
            self.vix['close']=value
            memory,event=transition(memory,self.signal(),self.now)
            self.assertEqual(event['kind'],kind)
        memory,event=transition(memory,self.signal(),self.now)
        self.assertIsNone(event)

    def test_recovery_two_distinct_observation_dates(self):
        memory={'last_valid':'risk'}
        memory,event=transition(memory,self.signal(),self.now)
        self.assertIsNone(event)
        memory,event=transition(memory,self.signal(),self.now)
        self.assertIsNone(event)
        self.now+=timedelta(days=1)
        self.market['fetched']=self.now.isoformat()
        for item in self.market['lamps'].values():item['date']='2026-10-17'
        memory,event=transition(memory,self.signal(),self.now)
        self.assertEqual(event['kind'],'positive')
        self.assertEqual(memory['level'],2)

    def test_first_good_state_never_claims_transition(self):
        memory,event=transition(None,self.signal(),self.now)
        self.assertIsNone(event)
        self.assertFalse(memory['positive_confirmed'])

    def test_unknown_resets_recovery(self):
        memory,_=transition({'last_valid':'risk'},self.signal(),self.now)
        memory,event=transition(memory,{'state':'unknown'},self.now)
        self.assertIsNone(event)
        self.assertEqual(memory['recovery_days'],[])
        self.assertEqual(memory['last_valid'],'risk')

    def test_incomplete_data_never_lowers_confirmed_level(self):
        signal=market_status({'close':22,'date':'2026-10-15'},None,self.now)
        memory,event=transition({'last_valid':'risk'},signal,self.now)
        self.assertIsNone(event)
        self.assertEqual(memory['last_valid'],'risk')

    def test_disabled_does_not_replay(self):
        self.vix['close']=35
        memory,event=transition(None,self.signal(),self.now,False)
        self.assertIsNone(event)
        memory,event=transition(memory,self.signal(),self.now,True)
        self.assertIsNone(event)
        self.assertEqual(len(memory['history']),1)

    def test_same_stage_reentry_same_day_suppressed(self):
        self.vix['close']=35
        memory,_=transition(None,self.signal(),self.now)
        memory['level']=2
        memory,event=transition(memory,self.signal(),self.now)
        self.assertIsNone(event)

    def test_concentration_uses_values_not_provider_weight(self):
        snap = {'fetched': self.now.isoformat(), 'positions': [
            {'code': 'A', 'name': '가상 A', 'value': 40, 'weight': 99},
            {'code': 'B', 'name': '가상 B', 'value': 30},
            {'code': 'C', 'name': '가상 C', 'value': 30}]}
        self.assertFalse(concentration(snap, self.now)['over'])
        snap['positions'][0]['value'] = 50
        self.assertTrue(concentration(snap, self.now)['over'])
        snap['fetched'] = (self.now - timedelta(minutes=16)).isoformat()
        self.assertIsNone(concentration(snap, self.now)['weight'])

    def test_duplicate_positions_are_combined(self):
        snap = {'fetched': self.now.isoformat(), 'positions': [
            {'code': 'A', 'value': 30}, {'code': 'A', 'value': 30}, {'code': 'B', 'value': 40}]}
        self.assertEqual(concentration(snap, self.now)['weight'], 60)

    def test_calendar_month_end_leap_year(self):
        result = month_end_check(datetime(2028, 2, 27).date())
        self.assertEqual(result, {'date': '2028-02-29', 'active': True})


if __name__ == '__main__': unittest.main()
