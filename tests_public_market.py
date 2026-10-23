import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from predash.public_market import parse_index
from predash.market import MarketDataError

class PublicMarketTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,16,18,tzinfo=ZoneInfo('Asia/Seoul'))
        self.xml='<protocol><chartdata>'+''.join(f'<item data="202609{d:02d}|1|2|1|{100+d}|10" />' for d in range(1,31))+'<item data="20261016|1|2|1|200|10" /></chartdata></protocol>'
    def test_latest_and_ma(self):
        result=parse_index(self.xml,'코스피',self.now)
        self.assertEqual(result['close'],200)
        self.assertEqual(result['date'],'2026-10-16')
        self.assertAlmostEqual(result['ma10'],(sum(range(122,131))+200)/10)
    def test_bad_xml(self):
        with self.assertRaises(MarketDataError):parse_index('<bad','코스피',self.now)
    def test_intraday_does_not_use_unconfirmed_bar(self):
        with self.assertRaises(MarketDataError):parse_index(self.xml,'코스피',self.now.replace(hour=10))
