"""PreDash status dashboard and dismissible market transition dialogs."""
import html
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from predash.alerts import market_status, transition, concentration, month_end_check, event_copy
from predash.macro import MacroError, VIX_URL

STYLE = '''<style>
:root{--pd-ink:#172b49;--pd-muted:#64748b;--pd-line:#e1e6ee;--pd-paper:#fff;--pd-base:#f6f8fb}
.stApp{background:var(--pd-base);color:var(--pd-ink);color-scheme:light}[data-testid="stHeader"]{background:#f6f8fb}
[data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,[data-testid="stMain"] [data-testid="stMetricValue"],[data-testid="stMain"] [data-testid="stMetricLabel"]{color:#172b49}
[role="dialog"]{background:#fff!important;color:#172b49!important}[role="dialog"] h2,[role="dialog"] p{color:#172b49!important}
[data-testid="stSidebar"]{background:#172b49;border:0}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] .pd-brand-note,[data-testid="stSidebar"] .pd-side-label{color:#eef4ff!important}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#284462;border-left-color:#25b9b4}
.pd-badge{background:#edf2f8;border-color:#dce4ed;color:#33445e}.pd-toolbar{border-color:#dce4ed}
.pd-summary{background:#172b49}.pd-v-panel,.pd-card,.pd-holding,.pd-watch,.pd-evidence{background:#fff;border-color:#e1e6ee;border-radius:12px}
.pd-v-note,.pd-v-empty{color:#64748b}.pd-v-empty{background:#f3f6fa}.pd-v-donut>div{background:white}
.pd-status-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 14px}
.pd-status-pill{border:1px solid #e1e6ee;border-radius:12px;padding:14px 16px;font-weight:700;color:#52617a;background:#edf2f8}
.pd-status-pill.risk{background:#fff0f0;color:#a12732;border-color:#f2c9ce}.pd-status-pill.caution{background:#fff6e8;color:#995713;border-color:#f1d8ac}
.pd-status-pill.alert{background:#fff0df;color:#9b4808;border-color:#efbe85}.pd-status-pill.safe,.pd-status-pill.positive{background:#eaf9f6;color:#087d77;border-color:#bce4de}
.pd-state-banner{border-radius:12px;border:1px solid #e1e6ee;background:#fff;padding:18px 22px;margin-bottom:14px}
.pd-state-banner.risk{border-left:5px solid #c54450;background:#fff5f5}.pd-state-banner.caution{border-left:5px solid #d38a28;background:#fffbf2}
.pd-state-banner.alert{border-left:5px solid #dc781e;background:#fff6ec}.pd-state-banner.safe,.pd-state-banner.positive{border-left:5px solid #0d9992;background:#f0fbf8}.pd-state-banner h3{margin:0 0 5px}
.pd-state-banner p{margin:4px 0}.pd-state-banner small{color:#64748b}
.pd-prime{border:1px solid #c4e1df;background:#f1faf9;border-radius:12px;padding:20px;color:#172b49}
.pd-prime strong{font-size:22px}.pd-prime p{margin:8px 0}.pd-prime small{color:#64748b}
.pd-alert-log{padding:10px 0;border-bottom:1px solid #e1e6ee}.pd-alert-log small{display:block;color:#64748b}
@media(max-width:760px){.pd-status-grid{grid-template-columns:1fr}.pd-status-pill{padding:10px 14px}}
</style>'''


def apply_workspace_style():
    st.html(STYLE)


def _navigate(target):
    st.session_state.navigation = target


@st.dialog('시장 상태 알림')
def market_dialog(event):
    if event['kind'] == 'positive':
        st.success(event['title'])
    elif event['kind'] == 'risk':
        st.error(event['title'])
    else:
        st.warning(event['title'])
    st.write(event_copy(event['kind']))
    st.markdown('**이번 안내의 근거**')
    for reason in event['reasons']:
        st.write('• ' + reason)
    st.caption('PreDash의 시장 공통 기준에 따른 안내입니다. 개인별 적합성·수익을 보장하지 않으며 주문은 전송하지 않습니다.')
    target = '투자 근거' if event['kind'] == 'positive' else '내 계좌'
    label = '투자 근거 확인하기' if event['kind'] == 'positive' else '보유 비중 점검하기'
    left, right = st.columns(2)
    if left.button(label, key='market_popup_review', on_click=_navigate, args=(target,), use_container_width=True):
        st.rerun()
    if right.button('확인했어요', key='market_popup_close', use_container_width=True):
        st.rerun()


@st.fragment(run_every=60)
def render_workspace(vix_loader, market_loader):
    """Refresh public context while the browser session is active; no background messaging."""
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    error = None
    try:
        vix = vix_loader(now.astimezone(ZoneInfo('America/New_York')).date())
    except MacroError as exc:
        vix, error = None, str(exc)
    market = market_loader()
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    signal = market_status(vix, market, now)
    with st.expander('알림 설정 · 상태 판단 기준', expanded=False):
        enabled = st.toggle('시장 전환 팝업 받기', value=True, key='market_popups_enabled')
        threshold = st.number_input('한 종목 집중도 기준 (%)', min_value=10, max_value=100,
                                    value=40, step=5, key='concentration_threshold')
        st.caption('VIX: 15 미만 안정 / 15 이상 주의 / 20 이상 경계 / 30 이상 위험. 국내 지수: 두 이동평균 위 안정, 사이·일치 주의, 모두 아래 경계. 가장 높은 단계를 적용합니다. 개선은 완전한 자료의 서로 다른 두 관측일에 확인합니다. VIX는 변동성 지표이며 매매 예측 공식이 아닙니다.')
        st.caption('VIX는 Cboe 일별 종가(30분 캐시), 국내 지수는 KIS 또는 네이버 금융 대체 자료(5분 재조회·출처 별도 표시). '
                   '앱을 열어 둔 동안 60초마다 확인하며 장중 실시간 신호·앱 종료 후 알림은 아닙니다. '
                   '팝업과 이력은 현재 접속 세션에서 관리합니다.')
    previous_level = (st.session_state.get('market_alert_memory') or {}).get('level')
    memory, event = transition(st.session_state.get('market_alert_memory'), signal, now, enabled)
    st.session_state.market_alert_memory = memory
    account = concentration(st.session_state.get('snapshot'), now, threshold)
    market_label = signal['label']
    if signal['level']:
        market_label = f"Level {signal['level']} · {market_label}"
    account_class = 'caution' if account['over'] else 'positive' if account['fresh'] else 'unknown'
    complete_label = '기준일 확인' if signal['complete'] else '일부 자료 확인 필요'
    e = html.escape
    st.html(f"<div class='pd-status-grid'><div class='pd-status-pill {signal['state']}'>● 시장 환경 · {market_label}</div>"
            f"<div class='pd-status-pill {account_class}'>● 계좌 집중도 · {e(account['label'])}</div>"
            f"<div class='pd-status-pill'>◷ 자료 상태 · {complete_label}</div></div>")
    title = {'risk':'시장 위험도가 높습니다', 'alert':'시장 경계 단계입니다',
             'caution':'신규 매수와 비중 확대에 신중하세요', 'safe':'시장 안정 조건입니다',
             'unknown':'시장 판단을 보류합니다'}[signal['state']]
    message = event_copy(signal['state']) if signal['state'] in ('risk', 'alert') else (
        '긍정 전환이 두 관측일에 확인됐습니다. 여유자금 범위에서 분할 투자를 검토하세요.'
        if memory.get('positive_confirmed') else
        '목표 비중과 분산 상태를 점검하세요. 안정 상태가 수익을 보장하지는 않습니다.'
        if signal['state'] == 'safe' else
        '신규 매수와 비중 확대를 서두르지 말고 투자 근거를 확인하세요.'
        if signal['state'] == 'caution' else
        '자료 누락 또는 기준일 불일치로 판단할 수 없습니다.')
    if memory.get('recovery_days'):
        message += ' 등급 개선 확인 중 · 서로 다른 두 관측일이 필요합니다.'
    if signal['level'] and memory.get('level', signal['level']) > signal['level']:
        title = '관측값 개선 중 · 확정 단계 하향 보류'
    if not signal['complete'] and signal['level']:
        title = signal['label']
    evidence = ' / '.join(signal['reasons']) or '검증 가능한 시장 자료 없음'
    st.html(f"<section class='pd-state-banner {signal['state']}'><h3>{title}</h3><p>{message}</p>"
            f"<small>{e(evidence)}</small></section>")
    st.caption('판정 시각(KST): ' + now.strftime('%Y-%m-%d %H:%M:%S') +
               ' · 이전 확정 단계: ' + str(previous_level or '없음') +
               ' · 현재 확정 단계: ' + str(memory.get('level') or '보류') +
               ' · 출처: Cboe VIX 일별 종가 / ' + str((market or {}).get('source') or '국내 지수 미확인'))
    columns = st.columns(3)
    with columns[0]:
        st.metric('VIX · 미국 종가', f"{signal['vix']:.2f}" if signal['vix'] is not None else '조회 불가')
        st.caption('기준일: ' + str((vix or {}).get('date') or '미확인'))
        st.link_button('Cboe 원자료', VIX_URL)
    for column, name in zip(columns[1:], ('코스피','코스닥')):
        item = ((market or {}).get('lamps') or {}).get(name) or {}
        with column:
            st.metric(name + ' · 지수 종가', f"{item['close']:,.2f}" if item.get('close') is not None else '조회 불가')
            st.caption('기준일: ' + str(item.get('date') or '미확인'))
            if item.get('ma10') is not None and item.get('ma20') is not None:
                st.write(f"10일선 {item['ma10']:,.2f} · 20일선 {item['ma20']:,.2f}")
            if item.get('source_url'):
                st.link_button(name + ' 원자료', item['source_url'])
            if item.get('rows'):
                st.line_chart(item['rows'],x='날짜',y='종가',height=160)
    st.caption('국내 지수 수집 시각: ' + str((market or {}).get('fetched') or '미확인'))
    if error:
        st.caption(error)
    if signal['missing']:
        st.caption('확인 필요 · ' + ', '.join(signal['missing']))
    left, middle, right = st.columns([1.2, 1.2, 1])
    with left:
        with st.container(border=True):
            st.subheader('자산 집중도')
            if account['weight'] is not None:
                st.metric('가장 큰 종목 비중', f"{account['weight']:.1f}%")
                st.write(account['name'])
                if account['over']:
                    st.warning(f'자산 집중 위험 · {threshold}% 기준 초과')
                st.progress(min(account['weight'] / 100, 1))
            else:
                st.write(account['label'])
            st.caption('국내주식 평가액 기준 · 현금·해외자산 제외 · 계좌 조회 후 15분까지 표시')
            if st.button('비중 점검하기', key='workspace_allocation', on_click=_navigate, args=('내 계좌',)):
                st.rerun()
    with middle:
        with st.container(border=True):
            st.subheader('이번 달 점검')
            month = month_end_check(now.date())
            st.write('입출금과 수익 구분 · 목표 비중 확인 · 월간 기록 정리')
            st.info(('월말 점검 기간 · ' if month['active'] else '월말 점검 예정 · ') + month['date'])
            st.caption('달력상 월말 기준 · 거래소 영업일을 의미하지 않습니다.')
            if st.button('나의 기록 확인', key='workspace_records', on_click=_navigate, args=('매매 습관',)):
                st.rerun()
    with right:
        st.html("<section class='pd-prime'><strong>PreDash Prime</strong><p>나의 투자 습관을 쌓는 30일</p>"
                "<p>심화 분석 · 계좌 점검 · 월간 기록</p><small>멤버십 기획 안내 · 결제·유료 권한은 적용하지 않았습니다.</small></section>")
        st.caption('시장 위험 표시와 기존 자료 조회는 계속 사용할 수 있습니다.')
    with st.expander('시장 흐름과 최근 알림', expanded=False):
        if vix and vix.get('rows'):
            st.line_chart(vix['rows'], x='날짜', y='VIX', height=180)
            st.link_button('Cboe VIX 원자료', VIX_URL)
        if not memory['history']:
            st.caption('현재 세션에서 기록된 상태 전환이 없습니다.')
        for item in memory['history'][:8]:
            st.html(f"<div class='pd-alert-log'>{e(item['title'])}<small>{e(item['at'])}</small></div>")
        if memory['history'] and st.button('최근 알림 다시 보기', key='market_popup_reopen'):
            event = memory['history'][0]
    if event:
        # Consume before opening: dismissing via X/ESC also won't reopen on the next rerun.
        market_dialog(event)
