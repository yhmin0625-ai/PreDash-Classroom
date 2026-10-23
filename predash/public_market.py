"""Public provider fallback; never substitute illustrative quotes."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
import requests
from predash.market import index_lamp, MarketDataError

URL = 'https://fchart.stock.naver.com/sise.nhn?symbol={symbol}&timeframe=day&count=90&requestType=0'


def parse_index(text, name, now):
    cutoff = now.astimezone(ZoneInfo('Asia/Seoul')).date()
    if now.astimezone(ZoneInfo('Asia/Seoul')).hour < 16:
        cutoff -= timedelta(days=1)
    try:
        root = ET.fromstring(text)
        rows = []
        for item in root.findall('.//item'):
            fields = item.attrib['data'].split('|')
            day = datetime.strptime(fields[0], '%Y%m%d').date()
            if day <= cutoff:
                rows.append({'stck_bsop_date': fields[0], 'bstp_nmix_prpr': fields[4]})
        result = index_lamp(rows, name, now.astimezone(ZoneInfo('Asia/Seoul')).date())
        if result is None:
            raise MarketDataError('최신 지수 20거래일 자료 부족')
        result['rows'] = sorted([{'날짜':datetime.strptime(r['stck_bsop_date'],'%Y%m%d').date().isoformat(),
                                '종가':float(r['bstp_nmix_prpr'])} for r in rows],key=lambda x:x['날짜'])[-60:]
        return result
    except (ET.ParseError, KeyError, IndexError, ValueError, TypeError) as exc:
        raise MarketDataError('네이버 금융 지수 날짜·종가 검증 실패') from exc


def fetch_public_market(now):
    lamps, failures = {}, {}
    for name, symbol in (('코스피','KOSPI'),('코스닥','KOSDAQ')):
        url = URL.format(symbol=symbol)
        try:
            response = requests.get(url,timeout=(5,15))
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise MarketDataError('지수 응답 크기 초과')
            lamps[name] = {**parse_index(response.text,name,now),
                           'source':'네이버 금융 일별 지수 · 공식 거래소 API 아님', 'source_url':url}
        except (requests.RequestException,MarketDataError) as exc:
            failures[name] = str(exc)
    return {'lamps':lamps,'failures':failures,'fetched':now.isoformat(),
            'source':'네이버 금융 일별 지수 · KIS 미연결 시 대체 조회'}
