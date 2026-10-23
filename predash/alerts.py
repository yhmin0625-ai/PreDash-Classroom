"""Dated market context and session-local transition alerts; no order execution."""
from datetime import date, datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

SEOUL = ZoneInfo('Asia/Seoul')


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (ValueError, TypeError):
        return None


def _day(value, today):
    try:
        day = date.fromisoformat(str(value))
        return day if 0 <= (today - day).days <= 5 else None
    except (ValueError, TypeError):
        return None


def market_status(vix, market, now):
    """Positive requires BOTH Korean indices and VIX, never VIX alone."""
    korea_day = now.astimezone(SEOUL).date()
    us_day = now.astimezone(ZoneInfo('America/New_York')).date()
    value = _number((vix or {}).get('close'))
    vix_day = _day((vix or {}).get('date'), us_day)
    valid_vix = value is not None and value > 0 and vix_day is not None
    lamps = (market or {}).get('lamps') or {}
    valid = {}
    try:
        fetched = datetime.fromisoformat(str((market or {}).get('fetched')))
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=SEOUL)
        fresh_fetch = timedelta(0) <= now - fetched <= timedelta(hours=24)
    except (ValueError, TypeError):
        fresh_fetch = False
    for name in ('코스피', '코스닥'):
        item = lamps.get(name) or {}
        close, fast, slow = (_number(item.get(k)) for k in ('close', 'ma10', 'ma20'))
        day = _day(item.get('date'), korea_day)
        if day == korea_day and now.astimezone(SEOUL).hour < 16:
            day = None  # Intraday daily bars are not confirmed closes.
        if fresh_fetch and day and all(v is not None and v > 0 for v in (close, fast, slow)):
            # Recompute from evidence; do not trust a cached label.
            direction = '상승' if close > max(fast, slow) else '하락' if close < min(fast, slow) else '횡보'
            valid[name] = {'date': day.isoformat(), 'direction': direction,
                           'close':close, 'ma10':fast, 'ma20':slow}
    reasons = []
    if valid_vix:
        reasons.append(f"VIX {value:.2f} · 미국 종가 {vix_day.isoformat()}")
    for name, info in valid.items():
        reasons.append(f"{name} {info['direction']} · 종가 {info['close']:.2f} / 10일선 {info['ma10']:.2f} / 20일선 {info['ma20']:.2f} · {info['date']}")
    complete = valid_vix and len(valid) == 2 and len({x['date'] for x in valid.values()}) == 1
    aligned = complete and abs((date.fromisoformat(valid['코스피']['date']) - vix_day).days) <= 3
    levels = ([4 if value >= 30 else 3 if value >= 20 else 2 if value >= 15 else 1] if valid_vix else [])
    levels += [3 if x['direction'] == '하락' else 2 if x['direction'] == '횡보' else 1 for x in valid.values()]
    level = max(levels, default=0)
    if not aligned and level < 3:
        level = None
    state = {1:'safe', 2:'caution', 3:'alert', 4:'risk'}.get(level, 'unknown')
    label = {1:'안정', 2:'주의', 3:'경계', 4:'위험'}.get(level, '판정 보류')
    if not aligned and level:
        label = '최소 ' + label + ' · 일부 자료 미확인'
    missing = [name for name in ('코스피', '코스닥') if name not in valid]
    if not valid_vix:
        missing.append('VIX')
    if valid_vix and len(valid) == 2 and not aligned:
        missing.append('시장별 기준일 일치 확인')
    positive = bool(aligned and value < 20 and all(x['direction'] == '상승' for x in valid.values()))
    return {'state': state, 'level': level, 'label': label, 'reasons': reasons, 'missing': missing,
            'positive': positive, 'complete': bool(aligned),
            'day': valid.get('코스피', {}).get('date') if aligned else None,
            'as_of': now.isoformat(), 'vix': value if valid_vix else None}


def transition(memory, signal, now, enabled=True):
    """Escalate immediately; lower only after two distinct, complete observation dates."""
    memory = dict(memory or {})
    memory['history'] = list(memory.get('history', []))
    ranks = {'safe':1, 'caution':2, 'alert':3, 'risk':4}
    current = signal['state']
    level = signal.get('level', ranks.get(current))
    old = memory.get('level', ranks.get(memory.get('last_valid')))
    event = None
    memory['positive_confirmed'] = False
    if level is None:
        memory['recovery_days'] = []
        memory['recovery_target'] = None
        return memory, None
    if old is None or level >= old:
        memory['recovery_days'] = []
        memory['recovery_target'] = None
        if level >= 3 and (old is None or level > old):
            event = {'kind':current, 'title':'시장 위험도가 높아졌습니다' if level == 4 else '시장 경계 단계에 진입했습니다'}
        memory['level'] = level
        memory['last_valid'] = current
    elif signal.get('complete'):
        target = (level, bool(signal.get('positive')))
        days = list(memory.get('recovery_days', [])) if memory.get('recovery_target') == target else []
        day = signal.get('day')
        if day and (not days or day > days[-1]):
            days.append(day)
        memory['recovery_target'] = target
        memory['recovery_days'] = days[-2:]
        if len(days) >= 2:
            memory['level'] = level
            memory['last_valid'] = current
            if signal.get('positive'):
                memory['positive_confirmed'] = True
                event = {'kind':'positive', 'title':'시장 흐름이 긍정적으로 전환됐습니다'}
            memory['recovery_days'] = []
    else:
        memory['recovery_days'] = []
        memory['recovery_target'] = None
    if event:
        event.update(at=now.isoformat(), reasons=list(signal['reasons']),
                     id=now.isoformat() + ':' + event['kind'])
        memory['history'] = ([event] + memory['history'])[:20]
        seen = list(memory.get('popup_days', []))
        key = now.astimezone(SEOUL).date().isoformat() + ':' + event['kind']
        repeated = key in seen
        memory['popup_days'] = (seen + [key])[-40:]
        if repeated:
            event = None
    return memory, event if enabled else None


def concentration(snapshot, now, threshold=40):
    """Domestic-stock valuation denominator only; never present stale account data as current."""
    result = {'label': '계좌 조회 전', 'weight': None, 'name': None, 'over': False, 'fresh': False}
    if not snapshot:
        return result
    try:
        fetched = datetime.fromisoformat(str(snapshot['fetched']))
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=SEOUL)
        if not timedelta(0) <= now - fetched <= timedelta(minutes=15):
            return {**result, 'label': '계좌 새로고침 필요'}
        positions = snapshot.get('positions') or []
        values = [_number(p.get('value')) for p in positions]
        if any(v is None or v < 0 for v in values):
            return {**result, 'label': '평가액 확인 필요'}
        # Aggregate duplicate lines for the same security before checking the largest weight.
        combined = {}
        for p, value in zip(positions, values):
            key = str(p.get('code') or '')
            if not key:
                return {**result, 'label': '종목코드 확인 필요'}
            item = combined.setdefault(key, {'name': str(p.get('name') or key), 'value': 0})
            item['value'] += value
        total = sum(values)
        if total <= 0:
            return {**result, 'label': '국내주식 평가액 없음', 'fresh': True}
        top = max(combined.values(), key=lambda x: x['value'])
        weight = top['value'] / total * 100
        over = weight > threshold
        return {'label': '집중도 점검' if over else '기준 이내', 'weight': weight,
                'name': top['name'], 'over': over, 'fresh': True}
    except (ValueError, KeyError, TypeError):
        return {**result, 'label': '계좌 자료 확인 필요'}


def month_end_check(today):
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    last = next_month - timedelta(days=1)
    # Calendar month-end reminder. No claim that this is an exchange trading day.
    return {'date': last.isoformat(), 'active': (last - today).days <= 3}


def event_copy(kind):
    if kind == 'risk':
        return ('보유 비중을 줄여 위험 노출을 낮추는 방안을 권장합니다. '
                '집중 종목과 현금 여력을 확인하고, 본인의 투자 계획에 따라 조정하세요.')
    if kind == 'alert':
        return ('추가 매수 속도를 늦추고 보유 비중 축소를 검토하는 것을 권장합니다. '
                '특히 한 종목에 집중된 비중과 감내 가능한 손실을 점검하세요.')
    return ('시장 흐름의 긍정 조건이 서로 다른 두 관측일에 확인됐습니다. '
            '여유자금 범위에서 분할 투자를 검토해 보세요. 종목의 실적·가격과 목표 비중을 함께 확인하세요.')
