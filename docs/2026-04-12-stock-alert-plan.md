# Stock Alert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 코스피 기술적 분석 기반 매수/매도 신호를 텔레그램으로 자동 알림하는 시스템 구축

**Architecture:** 모듈 분리 방식 — collector(수집) → analyzer(분석/필터링) → notifier(발송)을 main.py에서 순차 실행. GitHub Actions cron으로 평일 KST 16:30 자동 실행.

**Tech Stack:** Python 3.11, pykrx, pandas, python-telegram-bot, holidays, python-dotenv

---

## File Structure

| 파일 | 역할 |
|------|------|
| `config.py` | 조건값, 상수 설정 |
| `collector.py` | pykrx 데이터 수집 + 시가총액 필터 |
| `analyzer.py` | MA, RSI, 거래량 지표 계산 + 매수/매도 필터링 |
| `notifier.py` | 텔레그램 봇 메시지 발송 |
| `main.py` | 진입점: 공휴일 체크 → 수집 → 분석 → 발송 |
| `tests/test_analyzer.py` | analyzer 단위 테스트 |
| `tests/test_collector.py` | collector 단위 테스트 |
| `tests/test_notifier.py` | notifier 단위 테스트 |
| `requirements.txt` | 의존성 |
| `.github/workflows/daily-alert.yml` | GitHub Actions cron |
| `.env.example` | 환경변수 템플릿 |
| `.gitignore` | .env 등 제외 |

---

### Task 1: 프로젝트 초기화

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Git 레포 초기화**

```bash
cd ~/Documents/repo/stock-alert
git init
```

- [ ] **Step 2: .gitignore 생성**

```gitignore
.env
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 3: requirements.txt 생성**

```
pykrx>=1.0.45
pandas>=2.0.0
python-telegram-bot>=20.0
python-dotenv>=1.0.0
holidays>=0.50
pytest>=7.0.0
```

- [ ] **Step 4: .env.example 생성**

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

- [ ] **Step 5: config.py 생성**

```python
MARKET_CAP_MIN = 500_000_000_000  # 5,000억원

MA_SHORT = 5
MA_LONG = 20
MA_TREND = 60

RSI_PERIOD = 14
RSI_BUY_RANGE = (30, 50)
RSI_SELL_THRESHOLD = 70

VOLUME_RATIO_MIN = 1.5  # 150%
VOLUME_AVG_DAYS = 20

MAX_CANDIDATES = 30  # 매수/매도 각각
DATA_DAYS = 80  # 수집 일수 (MA60 + 여유분)
```

- [ ] **Step 6: 가상환경 세팅 및 의존성 설치**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 7: 커밋**

```bash
git add .gitignore requirements.txt config.py .env.example
git commit -m "chore: 프로젝트 초기화 - 의존성, 설정값, gitignore"
```

---

### Task 2: 데이터 수집 모듈 (collector.py)

**Files:**
- Create: `collector.py`
- Create: `tests/test_collector.py`

- [ ] **Step 1: 테스트 파일 생성 — 시가총액 필터링 테스트**

```python
# tests/test_collector.py
import pandas as pd
from unittest.mock import patch, MagicMock
from collector import filter_by_market_cap, collect_stock_data


def test_filter_by_market_cap():
    """시가총액 5000억 미만 종목이 필터링되는지 확인"""
    mock_cap_data = pd.DataFrame({
        "종목코드": ["005930", "000660", "999999"],
        "시가총액": [400_000_000_000_000, 100_000_000_000_000, 300_000_000_000],
    })
    with patch("collector.stock.get_market_cap_by_date") as mock_get_cap:
        mock_get_cap.return_value = pd.DataFrame(
            {"시가총액": [400_000_000_000_000, 100_000_000_000_000, 300_000_000_000]},
            index=["005930", "000660", "999999"],
        )
        result = filter_by_market_cap("20260410")
        assert "005930" in result
        assert "000660" in result
        assert "999999" not in result
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_collector.py::test_filter_by_market_cap -v
```

Expected: FAIL — `ImportError: cannot import name 'filter_by_market_cap' from 'collector'`

- [ ] **Step 3: collector.py 구현**

```python
# collector.py
from datetime import datetime, timedelta

import pandas as pd
from pykrx import stock

import config


def filter_by_market_cap(date: str) -> list[str]:
    """시가총액 기준 이상 종목코드 리스트 반환.

    Args:
        date: "YYYYMMDD" 형식 날짜

    Returns:
        종목코드 리스트 (예: ["005930", "000660", ...])
    """
    cap_df = stock.get_market_cap_by_date(date, date, "ALL")
    if cap_df.empty:
        return []
    filtered = cap_df[cap_df["시가총액"] >= config.MARKET_CAP_MIN]
    return filtered.index.tolist()


def collect_stock_data(tickers: list[str], end_date: str) -> dict[str, pd.DataFrame]:
    """종목별 일봉 데이터 수집.

    Args:
        tickers: 종목코드 리스트
        end_date: "YYYYMMDD" 형식 마지막 날짜

    Returns:
        {종목코드: DataFrame(시가,고가,저가,종가,거래량)} 딕셔너리
    """
    start_date = (
        datetime.strptime(end_date, "%Y%m%d") - timedelta(days=config.DATA_DAYS)
    ).strftime("%Y%m%d")

    result = {}
    for ticker in tickers:
        try:
            df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
            if not df.empty:
                result[ticker] = df
        except Exception:
            continue
    return result
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_collector.py -v
```

Expected: PASS

- [ ] **Step 5: 종목명 조회 헬퍼 테스트 추가**

```python
# tests/test_collector.py 에 추가
def test_get_ticker_name():
    """종목코드로 종목명을 조회하는지 확인"""
    with patch("collector.stock.get_market_ticker_name") as mock_name:
        mock_name.return_value = "삼성전자"
        from collector import get_ticker_name
        assert get_ticker_name("005930") == "삼성전자"
```

- [ ] **Step 6: get_ticker_name 구현**

```python
# collector.py 에 추가
def get_ticker_name(ticker: str) -> str:
    """종목코드로 종목명 반환."""
    return stock.get_market_ticker_name(ticker)
```

- [ ] **Step 7: 전체 테스트 통과 확인 및 커밋**

```bash
pytest tests/test_collector.py -v
git add collector.py tests/test_collector.py
git commit -m "feat: 데이터 수집 모듈 - 시가총액 필터 + 일봉 수집"
```

---

### Task 3: 분석 엔진 — 지표 계산 (analyzer.py)

**Files:**
- Create: `analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: 이동평균선 계산 테스트**

```python
# tests/test_analyzer.py
import pandas as pd
import numpy as np
from analyzer import calculate_moving_averages, calculate_rsi, calculate_volume_ratio


def make_sample_df(prices: list[float], volumes: list[int]) -> pd.DataFrame:
    """테스트용 OHLCV DataFrame 생성."""
    n = len(prices)
    dates = pd.date_range("2026-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "시가": prices,
            "고가": [p * 1.02 for p in prices],
            "저가": [p * 0.98 for p in prices],
            "종가": prices,
            "거래량": volumes,
        },
        index=dates,
    )


def test_calculate_moving_averages():
    """MA5, MA20, MA60 컬럼이 추가되는지 확인"""
    prices = list(range(100, 170))  # 70개 데이터
    volumes = [1000] * 70
    df = make_sample_df(prices, volumes)

    result = calculate_moving_averages(df)
    assert "MA5" in result.columns
    assert "MA20" in result.columns
    assert "MA60" in result.columns
    # MA5의 마지막 값 = 마지막 5개 종가 평균
    assert result["MA5"].iloc[-1] == np.mean(prices[-5:])
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_analyzer.py::test_calculate_moving_averages -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: 이동평균선 계산 구현**

```python
# analyzer.py
import pandas as pd
import numpy as np

import config


def calculate_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """MA5, MA20, MA60 컬럼 추가."""
    df = df.copy()
    df["MA5"] = df["종가"].rolling(window=config.MA_SHORT).mean()
    df["MA20"] = df["종가"].rolling(window=config.MA_LONG).mean()
    df["MA60"] = df["종가"].rolling(window=config.MA_TREND).mean()
    return df
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_analyzer.py::test_calculate_moving_averages -v
```

Expected: PASS

- [ ] **Step 5: RSI 계산 테스트**

```python
# tests/test_analyzer.py 에 추가
def test_calculate_rsi():
    """RSI가 0~100 범위이고 올바르게 계산되는지 확인"""
    # 계속 오르는 가격 → RSI가 높아야 함
    rising_prices = [100 + i * 2 for i in range(30)]
    df = make_sample_df(rising_prices, [1000] * 30)
    result = calculate_rsi(df)
    assert "RSI" in result.columns
    assert result["RSI"].iloc[-1] > 70

    # 계속 내리는 가격 → RSI가 낮아야 함
    falling_prices = [200 - i * 2 for i in range(30)]
    df2 = make_sample_df(falling_prices, [1000] * 30)
    result2 = calculate_rsi(df2)
    assert result2["RSI"].iloc[-1] < 30
```

- [ ] **Step 6: RSI 계산 구현**

```python
# analyzer.py 에 추가
def calculate_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """RSI(14) 컬럼 추가."""
    df = df.copy()
    delta = df["종가"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=config.RSI_PERIOD, min_periods=config.RSI_PERIOD).mean()
    avg_loss = loss.rolling(window=config.RSI_PERIOD, min_periods=config.RSI_PERIOD).mean()

    # Wilder's smoothing 적용 (첫 값 이후)
    for i in range(config.RSI_PERIOD, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (config.RSI_PERIOD - 1) + gain.iloc[i]) / config.RSI_PERIOD
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (config.RSI_PERIOD - 1) + loss.iloc[i]) / config.RSI_PERIOD

    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df
```

- [ ] **Step 7: RSI 테스트 통과 확인**

```bash
pytest tests/test_analyzer.py::test_calculate_rsi -v
```

Expected: PASS

- [ ] **Step 8: 거래량 비율 테스트**

```python
# tests/test_analyzer.py 에 추가
def test_calculate_volume_ratio():
    """거래량 비율이 올바르게 계산되는지 확인"""
    volumes = [1000] * 25 + [3000]  # 마지막날 거래량 3배
    prices = [100] * 26
    df = make_sample_df(prices, volumes)

    result = calculate_volume_ratio(df)
    assert "거래량비율" in result.columns
    # 마지막날: 3000 / mean(1000*20) = 3.0
    assert abs(result["거래량비율"].iloc[-1] - 3.0) < 0.01
```

- [ ] **Step 9: 거래량 비율 구현**

```python
# analyzer.py 에 추가
def calculate_volume_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """거래량비율 컬럼 추가 (당일거래량 / 20일평균거래량)."""
    df = df.copy()
    avg_volume = df["거래량"].rolling(window=config.VOLUME_AVG_DAYS).mean()
    df["거래량비율"] = df["거래량"] / avg_volume
    return df
```

- [ ] **Step 10: 전체 테스트 통과 및 커밋**

```bash
pytest tests/test_analyzer.py -v
git add analyzer.py tests/test_analyzer.py
git commit -m "feat: 분석 엔진 - MA, RSI, 거래량비율 지표 계산"
```

---

### Task 4: 분석 엔진 — 매수/매도 필터링

**Files:**
- Modify: `analyzer.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: 골든크로스/데드크로스 감지 테스트**

```python
# tests/test_analyzer.py 에 추가
from analyzer import detect_cross_signals


def test_detect_golden_cross():
    """MA5가 MA20을 상향 돌파하면 골든크로스 감지"""
    df = pd.DataFrame({
        "MA5": [95, 98, 101, 103],
        "MA20": [100, 100, 100, 100],
    })
    result = detect_cross_signals(df)
    assert result["골든크로스"].iloc[-2] is True or result["골든크로스"].iloc[2] == True
    assert result["데드크로스"].iloc[2] == False


def test_detect_dead_cross():
    """MA5가 MA20을 하향 돌파하면 데드크로스 감지"""
    df = pd.DataFrame({
        "MA5": [105, 102, 99, 97],
        "MA20": [100, 100, 100, 100],
    })
    result = detect_cross_signals(df)
    assert result["데드크로스"].iloc[2] == True
    assert result["골든크로스"].iloc[2] == False
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_analyzer.py::test_detect_golden_cross -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: 크로스 감지 구현**

```python
# analyzer.py 에 추가
def detect_cross_signals(df: pd.DataFrame) -> pd.DataFrame:
    """골든크로스/데드크로스 bool 컬럼 추가."""
    df = df.copy()
    prev_above = df["MA5"].shift(1) > df["MA20"].shift(1)
    curr_above = df["MA5"] > df["MA20"]

    df["골든크로스"] = (~prev_above) & curr_above
    df["데드크로스"] = prev_above & (~curr_above)
    return df
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_analyzer.py::test_detect_golden_cross tests/test_analyzer.py::test_detect_dead_cross -v
```

Expected: PASS

- [ ] **Step 5: 매수/매도 필터링 테스트**

```python
# tests/test_analyzer.py 에 추가
from analyzer import filter_buy_candidates, filter_sell_candidates


def test_filter_buy_candidates():
    """골든크로스 + RSI 30~50 + 거래량 150% 이상이면 매수 후보"""
    df = pd.DataFrame({
        "골든크로스": [False, True],
        "RSI": [60, 42.0],
        "거래량비율": [1.0, 2.3],
    })
    result = filter_buy_candidates(df)
    assert len(result) == 1
    assert result.iloc[0]["RSI"] == 42.0


def test_filter_buy_excludes_low_volume():
    """거래량 150% 미만이면 매수 후보에서 제외"""
    df = pd.DataFrame({
        "골든크로스": [True],
        "RSI": [42.0],
        "거래량비율": [1.2],
    })
    result = filter_buy_candidates(df)
    assert len(result) == 0


def test_filter_sell_candidates():
    """(데드크로스 OR RSI>=70) AND 거래량 150% 이상이면 매도 후보"""
    df = pd.DataFrame({
        "데드크로스": [True, False, False],
        "RSI": [50, 75, 75],
        "거래량비율": [2.0, 1.8, 1.2],
    })
    result = filter_sell_candidates(df)
    assert len(result) == 2  # 데드크로스+거래량 OK, RSI>=70+거래량 OK
```

- [ ] **Step 6: 매수/매도 필터링 구현**

```python
# analyzer.py 에 추가
def filter_buy_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """매수 후보 필터링: 골든크로스 AND RSI 범위 AND 거래량 조건."""
    rsi_min, rsi_max = config.RSI_BUY_RANGE
    mask = (
        df["골든크로스"]
        & (df["RSI"] >= rsi_min)
        & (df["RSI"] <= rsi_max)
        & (df["거래량비율"] >= config.VOLUME_RATIO_MIN)
    )
    return df[mask].sort_values("거래량비율", ascending=False).head(config.MAX_CANDIDATES)


def filter_sell_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """매도 후보 필터링: (데드크로스 OR RSI>=70) AND 거래량 조건."""
    mask = (
        (df["데드크로스"] | (df["RSI"] >= config.RSI_SELL_THRESHOLD))
        & (df["거래량비율"] >= config.VOLUME_RATIO_MIN)
    )
    return df[mask].sort_values("거래량비율", ascending=False).head(config.MAX_CANDIDATES)
```

- [ ] **Step 7: 전체 테스트 통과 및 커밋**

```bash
pytest tests/test_analyzer.py -v
git add analyzer.py tests/test_analyzer.py
git commit -m "feat: 매수/매도 필터링 - 골든/데드크로스, RSI, 거래량 조건"
```

---

### Task 5: 분석 파이프라인 통합 함수

**Files:**
- Modify: `analyzer.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: analyze_all 통합 함수 테스트**

```python
# tests/test_analyzer.py 에 추가
from analyzer import analyze_stock, analyze_all


def test_analyze_stock():
    """단일 종목 분석: 모든 지표 컬럼이 추가되는지 확인"""
    prices = list(range(100, 170))
    volumes = [1000] * 70
    df = make_sample_df(prices, volumes)

    result = analyze_stock(df)
    expected_cols = {"MA5", "MA20", "MA60", "RSI", "거래량비율", "골든크로스", "데드크로스"}
    assert expected_cols.issubset(set(result.columns))


def test_analyze_all_returns_candidates():
    """전체 분석 결과가 매수/매도 후보 딕셔너리를 반환하는지 확인"""
    # 골든크로스가 발생하도록 데이터 구성
    # MA5가 MA20 아래에서 위로 올라가는 패턴
    prices = [100] * 40 + [95, 94, 93, 94, 96, 98, 100, 102, 104, 106,
                            108, 110, 112, 114, 116, 118, 120, 122, 124, 126,
                            128, 130, 132, 134, 136, 138, 140, 142, 144, 146]
    volumes = [1000] * 60 + [3000] * 10
    df = make_sample_df(prices[:70], volumes[:70])
    stock_data = {"005930": df}

    result = analyze_all(stock_data)
    assert "buy" in result
    assert "sell" in result
    assert isinstance(result["buy"], list)
    assert isinstance(result["sell"], list)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_analyzer.py::test_analyze_stock -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: analyze_stock, analyze_all 구현**

```python
# analyzer.py 에 추가
def analyze_stock(df: pd.DataFrame) -> pd.DataFrame:
    """단일 종목에 모든 지표를 계산하여 반환."""
    df = calculate_moving_averages(df)
    df = calculate_rsi(df)
    df = calculate_volume_ratio(df)
    df = detect_cross_signals(df)
    return df


def analyze_all(stock_data: dict[str, pd.DataFrame]) -> dict[str, list[dict]]:
    """전체 종목 분석 후 매수/매도 후보 반환.

    Returns:
        {
            "buy": [{"ticker": "005930", "name": "삼성전자", "rsi": 42.3, ...}, ...],
            "sell": [...]
        }
    """
    all_last_rows = []

    for ticker, df in stock_data.items():
        try:
            analyzed = analyze_stock(df)
            if analyzed.empty:
                continue
            last_row = analyzed.iloc[-1].copy()
            last_row["ticker"] = ticker
            all_last_rows.append(last_row)
        except Exception:
            continue

    if not all_last_rows:
        return {"buy": [], "sell": []}

    combined = pd.DataFrame(all_last_rows)

    buy_df = filter_buy_candidates(combined)
    sell_df = filter_sell_candidates(combined)

    def to_list(df: pd.DataFrame) -> list[dict]:
        records = []
        for _, row in df.iterrows():
            records.append({
                "ticker": row["ticker"],
                "rsi": round(row["RSI"], 1),
                "volume_ratio": round(row["거래량비율"], 1),
                "golden_cross": bool(row.get("골든크로스", False)),
                "dead_cross": bool(row.get("데드크로스", False)),
                "close": int(row["종가"]),
            })
        return records

    return {"buy": to_list(buy_df), "sell": to_list(sell_df)}
```

- [ ] **Step 4: 전체 테스트 통과 및 커밋**

```bash
pytest tests/test_analyzer.py -v
git add analyzer.py tests/test_analyzer.py
git commit -m "feat: 분석 파이프라인 통합 - analyze_stock, analyze_all"
```

---

### Task 6: 텔레그램 발송 모듈 (notifier.py)

**Files:**
- Create: `notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: 메시지 포매팅 테스트**

```python
# tests/test_notifier.py
from notifier import format_message


def test_format_message_with_candidates():
    """매수/매도 후보가 있을 때 메시지 포맷 확인"""
    candidates = {
        "buy": [
            {"ticker": "005930", "name": "삼성전자", "rsi": 42.3, "volume_ratio": 2.3,
             "golden_cross": True, "dead_cross": False, "close": 71000},
        ],
        "sell": [
            {"ticker": "000660", "name": "SK하이닉스", "rsi": 75.2, "volume_ratio": 1.8,
             "golden_cross": False, "dead_cross": False, "close": 150000},
        ],
    }
    result = format_message(candidates)
    assert "매수 후보" in result
    assert "삼성전자" in result
    assert "매도 후보" in result
    assert "SK하이닉스" in result


def test_format_message_empty():
    """후보가 없을 때 메시지 확인"""
    candidates = {"buy": [], "sell": []}
    result = format_message(candidates)
    assert "후보가 없습니다" in result
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_notifier.py::test_format_message_with_candidates -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: format_message 구현**

```python
# notifier.py
import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_MAX_LENGTH = 4096


def format_message(candidates: dict[str, list[dict]]) -> str:
    """매수/매도 후보를 텔레그램 메시지 문자열로 포매팅."""
    buy = candidates["buy"]
    sell = candidates["sell"]

    if not buy and not sell:
        return "오늘은 매수/매도 후보가 없습니다."

    lines = []

    if buy:
        lines.append(f"📈 매수 후보 ({len(buy)}종목)")
        for i, item in enumerate(buy, 1):
            signals = []
            if item["golden_cross"]:
                signals.append("골든크로스")
            signals.append(f"RSI {item['rsi']}")
            signals.append(f"거래량 {int(item['volume_ratio'] * 100)}%")
            lines.append(f"{i}. {item['name']} ({item['ticker']})")
            lines.append(f"   {' | '.join(signals)} | 종가 {item['close']:,}원")
        lines.append("")

    if sell:
        lines.append(f"📉 매도 후보 ({len(sell)}종목)")
        for i, item in enumerate(sell, 1):
            signals = []
            if item["dead_cross"]:
                signals.append("데드크로스")
            if item["rsi"] >= 70:
                signals.append(f"RSI {item['rsi']}")
            signals.append(f"거래량 {int(item['volume_ratio'] * 100)}%")
            lines.append(f"{i}. {item['name']} ({item['ticker']})")
            lines.append(f"   {' | '.join(signals)} | 종가 {item['close']:,}원")

    return "\n".join(lines)
```

- [ ] **Step 4: 포맷 테스트 통과 확인**

```bash
pytest tests/test_notifier.py -v
```

Expected: PASS

- [ ] **Step 5: 메시지 분할 테스트**

```python
# tests/test_notifier.py 에 추가
from notifier import split_message, TELEGRAM_MAX_LENGTH


def test_split_message_short():
    """짧은 메시지는 분할하지 않음"""
    msg = "짧은 메시지"
    result = split_message(msg)
    assert result == [msg]


def test_split_message_long():
    """긴 메시지는 4096자 기준으로 분할"""
    msg = "테스트 라인\n" * 1000  # 충분히 긴 메시지
    result = split_message(msg)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= TELEGRAM_MAX_LENGTH
```

- [ ] **Step 6: split_message 구현**

```python
# notifier.py 에 추가
def split_message(message: str) -> list[str]:
    """텔레그램 글자 제한(4096자)에 맞게 메시지를 줄 단위로 분할."""
    if len(message) <= TELEGRAM_MAX_LENGTH:
        return [message]

    chunks = []
    current = ""
    for line in message.split("\n"):
        if len(current) + len(line) + 1 > TELEGRAM_MAX_LENGTH:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
```

- [ ] **Step 7: 텔레그램 발송 함수 구현**

```python
# notifier.py 에 추가
import asyncio
from telegram import Bot


async def _send_telegram(message: str) -> None:
    """텔레그램 메시지 발송 (내부용)."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chunks = split_message(message)
    for chunk in chunks:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk)


def send_alert(candidates: dict[str, list[dict]]) -> None:
    """매수/매도 후보를 텔레그램으로 발송. 실패 시 1회 재시도."""
    message = format_message(candidates)
    for attempt in range(2):
        try:
            asyncio.run(_send_telegram(message))
            return
        except Exception as e:
            if attempt == 0:
                continue
            raise RuntimeError(f"텔레그램 발송 실패: {e}")


def send_error(error_msg: str) -> None:
    """에러 메시지를 텔레그램으로 발송."""
    try:
        asyncio.run(_send_telegram(f"⚠️ Stock Alert 오류\n{error_msg}"))
    except Exception:
        pass
```

- [ ] **Step 8: 전체 테스트 통과 및 커밋**

```bash
pytest tests/test_notifier.py -v
git add notifier.py tests/test_notifier.py
git commit -m "feat: 텔레그램 발송 모듈 - 포매팅, 분할, 발송"
```

---

### Task 7: 메인 진입점 (main.py)

**Files:**
- Create: `main.py`

- [ ] **Step 1: main.py 구현**

```python
# main.py
import sys
from datetime import datetime

import holidays

from collector import filter_by_market_cap, collect_stock_data, get_ticker_name
from analyzer import analyze_all
from notifier import send_alert, send_error


def is_korean_holiday(date: datetime) -> bool:
    """한국 공휴일 여부 확인."""
    kr_holidays = holidays.KR(years=date.year)
    return date.date() in kr_holidays


def main() -> None:
    today = datetime.now()

    # 공휴일 체크
    if is_korean_holiday(today):
        print("오늘은 공휴일입니다. 종료합니다.")
        return

    today_str = today.strftime("%Y%m%d")
    print(f"[{today_str}] Stock Alert 시작")

    try:
        # 1. 데이터 수집
        print("시가총액 필터링 중...")
        tickers = filter_by_market_cap(today_str)
        if not tickers:
            send_error("시가총액 필터링 결과 종목이 없습니다.")
            return
        print(f"대상 종목: {len(tickers)}개")

        print("일봉 데이터 수집 중...")
        stock_data = collect_stock_data(tickers, today_str)
        if not stock_data:
            send_error("일봉 데이터 수집에 실패했습니다.")
            return
        print(f"수집 완료: {len(stock_data)}개")

        # 2. 분석
        print("분석 중...")
        candidates = analyze_all(stock_data)

        # 종목명 추가
        for category in ["buy", "sell"]:
            for item in candidates[category]:
                item["name"] = get_ticker_name(item["ticker"])

        print(f"매수 후보: {len(candidates['buy'])}개, 매도 후보: {len(candidates['sell'])}개")

        # 3. 텔레그램 발송
        print("텔레그램 발송 중...")
        send_alert(candidates)
        print("완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 로컬 테스트 실행**

```bash
python main.py
```

Note: 텔레그램 토큰 없이 실행하면 발송 단계에서 에러 발생 — 수집/분석까지 정상 동작하는지 확인

- [ ] **Step 3: 커밋**

```bash
git add main.py
git commit -m "feat: 메인 진입점 - 공휴일 체크 + 수집 → 분석 → 발송 파이프라인"
```

---

### Task 8: 텔레그램 봇 세팅

- [ ] **Step 1: 텔레그램에서 @BotFather 검색 후 봇 생성**

1. 텔레그램에서 @BotFather 에게 `/newbot` 명령
2. 봇 이름 입력 (예: `Stock Alert`)
3. 봇 username 입력 (예: `my_stock_alert_bot`)
4. **BOT_TOKEN** 을 받아서 메모

- [ ] **Step 2: CHAT_ID 확인**

1. 생성된 봇에게 아무 메시지 전송
2. 브라우저에서 `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` 접속
3. JSON 응답에서 `"chat":{"id": 숫자}` 부분의 숫자가 **CHAT_ID**

- [ ] **Step 3: .env 파일 생성**

```bash
cp .env.example .env
```

`.env` 파일에 실제 값 입력:
```
TELEGRAM_BOT_TOKEN=실제_봇_토큰
TELEGRAM_CHAT_ID=실제_채팅_아이디
```

- [ ] **Step 4: 발송 테스트**

```bash
python -c "
from notifier import send_error
send_error('테스트 메시지입니다!')
"
```

텔레그램에서 "⚠️ Stock Alert 오류\n테스트 메시지입니다!" 수신 확인

- [ ] **Step 5: 전체 파이프라인 테스트**

```bash
python main.py
```

텔레그램에서 매수/매도 후보 메시지 수신 확인

---

### Task 9: GitHub Actions 워크플로우

**Files:**
- Create: `.github/workflows/daily-alert.yml`

- [ ] **Step 1: 워크플로우 파일 생성**

```yaml
# .github/workflows/daily-alert.yml
name: Daily Stock Alert

on:
  schedule:
    - cron: '30 7 * * 1-5'  # UTC 07:30 = KST 16:30, 평일만
  workflow_dispatch:  # 수동 실행 가능

jobs:
  alert:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run stock alert
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python main.py
```

- [ ] **Step 2: 커밋**

```bash
mkdir -p .github/workflows
git add .github/workflows/daily-alert.yml
git commit -m "ci: GitHub Actions 워크플로우 - 평일 KST 16:30 자동 실행"
```

- [ ] **Step 3: GitHub 레포 생성 및 푸시**

```bash
gh repo create stock-alert --private --source=. --push
```

- [ ] **Step 4: GitHub Secrets 등록**

```bash
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHAT_ID
```

각각 프롬프트에 실제 값 입력

- [ ] **Step 5: 수동 실행으로 동작 확인**

```bash
gh workflow run daily-alert.yml
gh run list --workflow=daily-alert.yml --limit=1
```

GitHub Actions 실행 완료 후 텔레그램 수신 확인

---

### Task 10: 최종 검증

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest tests/ -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 2: 로컬 전체 파이프라인 실행**

```bash
python main.py
```

텔레그램 메시지 수신 확인

- [ ] **Step 3: GitHub Actions 수동 실행 확인**

```bash
gh workflow run daily-alert.yml
```

Actions 로그 정상 + 텔레그램 수신 확인

- [ ] **Step 4: 최종 커밋**

```bash
git add -A
git commit -m "docs: README 및 최종 정리"
```
