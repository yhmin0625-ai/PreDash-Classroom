"""Explicit synthetic UI preview; never loaded by the production app."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
from predash.workspace_ui import apply_workspace_style, render_workspace

st.set_page_config(page_title='PreDash · 팝업 동작 미리보기', layout='wide')
apply_workspace_style()
st.title('PreDash · 내 계좌 점검실')
st.warning('디자인·동작 검증용 합성 자료입니다. 실제 시장·계좌·투자 신호가 아닙니다.')
with st.sidebar:
    st.title('PreDash')
    st.radio('메뉴', ['오늘의 점검', '내 계좌', '투자 근거', '매매 습관'], key='navigation')
    scenario = st.selectbox('합성 자료 시나리오', ['위험', '경계', '주의', '안정', '긍정 전환', '자료 없음'])
now = datetime.now(ZoneInfo('Asia/Seoul'))
if st.session_state.get('preview_scenario') != scenario:
    st.session_state.preview_scenario = scenario
    st.session_state.market_alert_memory = (
        {'last_valid': 'risk', 'recovery_target': (2, True), 'recovery_days': [(now.date() - timedelta(days=2)).isoformat()]}
        if scenario == '긍정 전환' else {})
st.session_state.snapshot = {'fetched': now.isoformat(), 'positions': [
    {'code': 'DEMO-A', 'name': '가상 A종목', 'value': 45},
    {'code': 'DEMO-B', 'name': '가상 B종목', 'value': 30},
    {'code': 'DEMO-C', 'name': '가상 C종목', 'value': 25}]}


def demo_vix(day):
    if scenario == '자료 없음': return None
    value = {'위험': 32.4, '경계': 22.4, '주의': 16.4, '안정': 13.4, '긍정 전환': 18.2}[scenario]
    return {'close': value, 'date': day.isoformat(), 'rows': [
        {'날짜': (day - timedelta(days=19-i)).isoformat(), 'VIX': value + (19-i)*0.2}
        for i in range(20)]}


def demo_market():
    if scenario == '자료 없음': return None
    return {'fetched': now.isoformat(), 'lamps': {
        name: {'close': 130, 'ma10': 120, 'ma20': 110, 'date': (now.date()-timedelta(days=1)).isoformat()}
        for name in ('코스피', '코스닥')}}


render_workspace(demo_vix, demo_market)
st.caption('현재 선택 화면: ' + st.session_state.navigation + ' · 이 미리보기에는 실제 계좌 연결이 없습니다.')
