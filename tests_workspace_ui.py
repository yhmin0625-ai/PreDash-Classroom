"""Modal/navigation integration tests use explicit synthetic market fixtures."""
import unittest
from streamlit.testing.v1 import AppTest

SOURCE = '''
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from predash.workspace_ui import apply_workspace_style, render_workspace
st.radio('메뉴', ['오늘의 점검','내 계좌','투자 근거','매매 습관'],key='navigation')
apply_workspace_style()
now=datetime.now(ZoneInfo('Asia/Seoul'))
if 'seed' not in st.session_state:
    st.session_state.seed=True
    if st.session_state.get('scenario')=='positive':
        st.session_state.market_alert_memory={'last_valid':'risk','recovery_target': (2, True), 'recovery_days':[(now.date()-timedelta(days=2)).isoformat()]}
def vix_loader(day):
    return {'close':18 if st.session_state.get('scenario')=='positive' else 35,'date':day.isoformat(),'rows':[]}
def market_loader():
    return {'fetched':now.isoformat(),'lamps':{name:{'close':130,'ma10':120,'ma20':110,'date':(now.date()-timedelta(days=1)).isoformat()} for name in ('코스피','코스닥')}}
render_workspace(vix_loader,market_loader)
'''


class WorkspaceUI(unittest.TestCase):
    def test_risk_dialog_close_does_not_reopen(self):
        app = AppTest.from_string(SOURCE).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any('시장 위험도가 높아졌습니다' in e.value for e in app.error))
        next(b for b in app.button if b.key == 'market_popup_close').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(any(b.key == 'market_popup_close' for b in app.button))

    def test_popup_navigates_to_account_review(self):
        app = AppTest.from_string(SOURCE).run(timeout=20)
        next(b for b in app.button if b.key == 'market_popup_review').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['navigation'], '내 계좌')

    def test_confirmed_positive_popup_and_navigation(self):
        app = AppTest.from_string(SOURCE)
        app.session_state.scenario = 'positive'
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any('긍정적으로 전환' in e.value for e in app.success))
        next(b for b in app.button if b.key == 'market_popup_review').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['navigation'], '투자 근거')


if __name__ == '__main__': unittest.main()
