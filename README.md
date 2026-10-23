# STOCK INTELLIGENCE

주식 종합 분석 Streamlit 대시보드 (1차 데모).

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

현재 표시하는 가격과 재무 수치는 **가상 예시 데이터**입니다. 실제 투자 판단에 사용하지 마세요.

## Streamlit Cloud 배포

1. 이 파일들을 GitHub 저장소 루트에 업로드합니다.
2. Streamlit Community Cloud에서 New app을 선택합니다.
3. 저장소 `yhmin0625-ai/stock-intelligence-dashboard`, 브랜치 `main`, 파일 `app.py`를 선택합니다.
4. Deploy를 누릅니다. 비공개 저장소는 연결된 GitHub 앱의 저장소 접근 권한이 필요할 수 있습니다.

## API 보안

`.env`와 `.streamlit/secrets.toml`은 커밋하지 마세요. API 키는 Streamlit Cloud의 Secrets에서 관리합니다. 아직 실데이터 API는 연결하지 않았습니다.
