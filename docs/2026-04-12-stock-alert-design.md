# Stock Alert - 설계 문서

## 개요

코스피 시장의 기술적 분석 기반 매수/매도 신호를 자동으로 감지하여 텔레그램으로 알림을 보내는 시스템.
스윙매매(약 1주일 단위) 용도로, 개인 전용.

## 프로젝트 위치

`~/Documents/repo/stock-alert/`

## 파일 구조

```
stock-alert/
├── main.py              # 진입점: 수집 → 분석 → 발송
├── collector.py         # pykrx로 코스피 일봉 데이터 수집
├── analyzer.py          # MA, RSI, 거래량 지표 계산 + 필터링
├── notifier.py          # 텔레그램 봇 발송
├── config.py            # 조건값, 설정
├── requirements.txt     # 의존성
├── .github/
│   └── workflows/
│       └── daily-alert.yml  # GitHub Actions cron
└── .env                 # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (git 미포함)
```

## 1. 데이터 수집 (collector.py)

- **라이브러리**: pykrx
- **대상**: 코스피 전 종목 중 시가총액 5,000억원 이상 (약 150~200개)
- **시가총액 필터를 수집 단계에서 적용**: 불필요한 API 호출 감소
- **수집 데이터**: 60일치 일봉 (시가, 고가, 저가, 종가, 거래량)
- **DATA_DAYS**: 80일 요청 (MA60 계산 여유분 포함)
- **반환값**: `{종목코드: DataFrame}` 딕셔너리

## 2. 분석 엔진 (analyzer.py)

### 지표 계산

| 지표 | 설정 |
|------|------|
| 이동평균선 | MA5, MA20, MA60 |
| 골든크로스 | MA5가 MA20을 아래→위로 돌파 (당일) |
| 데드크로스 | MA5가 MA20을 위→아래로 돌파 (당일) |
| RSI | 14일 기준 |
| 거래량 비율 | 당일 거래량 / 직전 20일 평균 거래량 (당일 제외) |

### 필터링 조건

**매수 후보 (AND 조건):**
- 골든크로스 발생 (당일)
- RSI 30~50 (과매도 탈출 구간)
- 거래량 비율 150% 이상

**매도 후보:**
- (데드크로스 발생 OR RSI >= 70) AND 거래량 비율 150% 이상

### 정렬 및 제한

- 거래량 비율 높은 순 정렬
- 매수/매도 각각 최대 30개

### 튜닝 참고

초기 조건이 빡빡하여 매수 후보가 0~3개/일로 적을 수 있음. 필요 시 config.py에서 조정:
- 골든크로스 당일 → 최근 3일 이내로 확대
- RSI 30~50 → 25~55로 범위 확대
- 거래량 150% → 120%로 하향

## 3. 텔레그램 발송 (notifier.py)

- **라이브러리**: python-telegram-bot
- **인증**: BOT_TOKEN, CHAT_ID를 환경변수(.env)에서 로드
- **메시지 포맷** (마크다운):

```
📈 매수 후보 (3종목)
1. 삼성전자 (005930)
   골든크로스 | RSI 42.3 | 거래량 230%
2. ...

📉 매도 후보 (2종목)
1. ...
```

- 조건 충족 종목 없으면: "오늘은 매수/매도 후보가 없습니다"
- 텔레그램 글자 제한(4,096자) 초과 시 분할 발송
- 발송 실패 시 1회 재시도

## 4. 설정 (config.py)

```python
MARKET_CAP_MIN = 500_000_000_000   # 5,000억원
MA_SHORT = 5
MA_LONG = 20
MA_TREND = 60
RSI_PERIOD = 14
RSI_BUY_RANGE = (30, 50)
RSI_SELL_THRESHOLD = 70
VOLUME_RATIO_MIN = 1.5             # 150%
VOLUME_AVG_DAYS = 20
MAX_CANDIDATES = 30                # 매수/매도 각각
DATA_DAYS = 80                     # 수집 일수 (MA60 + 여유분)
```

## 5. 실행 환경 (GitHub Actions)

- **스케줄**: `cron "30 7 * * 1-5"` (UTC 07:30 = KST 16:30)
- **KST 16:30 이유**: 장 마감(15:30) 후 1시간 여유로 pykrx 데이터 안정적 반영
- **공휴일 처리**: `holidays` 라이브러리로 한국 공휴일 판별, 해당 시 조기 종료
- **시크릿**: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID를 GitHub Secrets에 등록

### 워크플로우 단계

1. Python 3.11 세팅
2. pip install -r requirements.txt
3. python main.py

## 6. 에러 처리 (main.py)

- 데이터 수집 실패 (pykrx 응답 없음): 텔레그램으로 에러 메시지 발송 후 종료
- 분석 중 개별 종목 에러: 해당 종목 스킵, 나머지 계속 진행
- 텔레그램 발송 실패: 1회 재시도 후 실패 시 GitHub Actions 로그에 기록

## 7. 의존성

```
pykrx
pandas
python-telegram-bot
python-dotenv
holidays
```

## 8. 향후 확장 (2차)

- 기본적 분석 데이터 추가 (PER, PBR, 영업이익 - DART/FinanceDataReader)
- HTML 리포트 생성 (상세 차트/테이블)
- 골든크로스 감지 범위 확대 (당일 → N일 이내) 옵션
