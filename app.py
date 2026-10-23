import streamlit as st
import pandas as pd
from services.sample_data import STOCKS, history, fundamentals

st.set_page_config(page_title='STOCK INTELLIGENCE', page_icon='📈', layout='wide')
st.title('📈 STOCK INTELLIGENCE')
st.caption('주식 종합 분석 대시보드 · 현재는 교육용 예시 데이터이며 실제 시세/투자 조언이 아닙니다.')

page = st.sidebar.radio('메뉴', ['종합 현황', '종목 분석', '기업 실적', '가치 평가', '관심종목', 'API 연결 상태'])
selected = st.sidebar.selectbox('분석 종목', list(STOCKS), format_func=lambda x: f'{STOCKS[x]} ({x})')
prices = history(selected)
financials = fundamentals(selected)

if page == '종합 현황':
    st.subheader('관심 시장 개요')
    st.info('현재 모든 수치는 데모 데이터입니다. 실제 금융 API 연동은 다음 단계에서 진행합니다.')
    a,b,c = st.columns(3)
    a.metric('분석 가능 종목', f'{len(STOCKS)}개')
    b.metric('데이터 모드', 'DEMO')
    c.metric('API 상태', '미연결')
    st.dataframe(pd.DataFrame([{'종목코드':k,'기업명':v} for k,v in STOCKS.items()]), hide_index=True, use_container_width=True)
elif page == '종목 분석':
    st.subheader(f'{STOCKS[selected]} ({selected})')
    st.line_chart(prices.set_index('날짜')['가격'])
    st.caption('가상의 일별 가격입니다. 실제 주가·수정주가가 아닙니다.')
elif page == '기업 실적':
    st.subheader(f'{STOCKS[selected]} 실적 추이')
    st.dataframe(financials, hide_index=True, use_container_width=True)
    st.bar_chart(financials.set_index('연도')[['매출액(억원)', '영업이익(억원)']])
    st.caption('실적 수치는 예시이며 공시 자료가 아닙니다.')
elif page == '가치 평가':
    st.subheader('가치평가 준비 화면')
    st.warning('실제 재무·시세 데이터가 연결되기 전에는 적정주가를 계산하지 않습니다.')
    st.write('예정 분석: PER, PBR, 영업이익 성장률, 경쟁사 비교 및 가정별 추정 가치')
elif page == '관심종목':
    st.subheader('관심종목 선택')
    picks = st.multiselect('종목을 선택하세요', list(STOCKS), default=list(STOCKS)[:2], format_func=lambda x: STOCKS[x])
    st.dataframe(pd.DataFrame([{'종목코드':p, '기업명':STOCKS[p]} for p in picks]), hide_index=True, use_container_width=True)
    st.caption('선택 정보는 현재 화면에만 적용되며 영구 저장되지 않습니다.')
else:
    st.subheader('API 연결 상태')
    st.dataframe(pd.DataFrame([{'서비스':s,'상태':'미연결','설명':d} for s,d in [
        ('OpenDART','재무제표·공시'),('공공데이터포털','일별 주가'),('KRX','시장·수급'),('관세청','수출입'),('OpenAI','공시 분석')]]),hide_index=True,use_container_width=True)
    st.info('키를 앱 화면이나 GitHub 코드에 직접 입력하지 마세요. 다음 단계에서 Streamlit Secrets를 연결합니다.')
