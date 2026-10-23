"""Live public market view. No synthetic quotes or account holdings."""
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from predash.macro import fetch_vix
from predash.public_market import fetch_public_market
from predash.workspace_ui import apply_workspace_style, render_workspace

st.set_page_config(page_title='PreDash · 최신 시장 점검',layout='wide')
apply_workspace_style()
with st.sidebar:
    st.title('PreDash')
    st.radio('메뉴',['오늘의 점검','내 계좌','투자 근거','매매 습관'],key='navigation')
    st.caption('실제 공개 자료 · 계좌 미연결')
st.title('PreDash · 오늘의 시장 점검')
st.caption('최신 조회 가능한 종가 기준 · 예시 수치와 가상 계좌는 사용하지 않습니다.')

@st.cache_data(ttl=1800)
def vix_loader(day):return fetch_vix(day)

@st.cache_data(ttl=300)
def market_loader():return fetch_public_market(datetime.now(ZoneInfo('Asia/Seoul')))

if st.button('최신 자료 다시 조회'):
    vix_loader.clear()
    market_loader.clear()
render_workspace(vix_loader,market_loader)
if st.session_state.navigation != '오늘의 점검':
    st.info('이 화면은 공개 시장 자료 확인용입니다. 개인 계좌·투자 근거는 본 앱의 연결 설정을 이용하세요.')
