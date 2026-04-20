# 시장별 시가총액 기준
MARKET_CAP_KOSPI = 1_000_000_000_000  # 1조원
MARKET_CAP_KOSDAQ = 500_000_000_000   # 5000억원

# 기존 상수 호환용 (사용처에서 KOSPI 기준으로 참조)
MARKET_CAP_MIN = MARKET_CAP_KOSPI

MA_SHORT = 5
MA_LONG = 20
MA_TREND = 60

RSI_PERIOD = 14
RSI_BUY_RANGE = (25, 55)
RSI_SELL_THRESHOLD = 70

VOLUME_RATIO_MIN = 1.2  # 120%

GOLDEN_CROSS_DAYS = 1  # 골든크로스 당일만
VOLUME_AVG_DAYS = 20

MAX_CANDIDATES = 30  # 매수/매도 각각
DATA_DAYS = 80  # 수집 일수 (MA60 + 여유분)

# 지지선/손절/목표가
SUPPORT_LOOKBACK = 20      # 지지선 탐지용 최근 거래일 수
STOP_LOSS_PCT = 0.03       # 손절: 진입가 -3%
TAKE_PROFIT_PCT = 0.06     # 목표: 진입가 +6% (손익비 1:2)
