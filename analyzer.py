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


def calculate_volume_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """거래량비율 컬럼 추가 (당일거래량 / 직전 20일평균거래량)."""
    df = df.copy()
    avg_volume = df["거래량"].shift(1).rolling(window=config.VOLUME_AVG_DAYS).mean()
    df["거래량비율"] = df["거래량"] / avg_volume
    return df


def detect_cross_signals(df: pd.DataFrame) -> pd.DataFrame:
    """골든크로스/데드크로스 bool 컬럼 추가."""
    df = df.copy()
    prev_above = df["MA5"].shift(1) > df["MA20"].shift(1)
    curr_above = df["MA5"] > df["MA20"]

    df["골든크로스"] = (~prev_above) & curr_above
    df["데드크로스"] = prev_above & (~curr_above)
    return df


def calculate_support_level(df: pd.DataFrame) -> float | None:
    """현재가 아래에서 가장 가까운 지지선 추정.

    후보: 최근 N일 저가 최저값, MA20
    두 후보 중 현재가 아래에 있는 값들 중 최대값(가장 근접한 지지).
    후보가 없으면 None.
    """
    if df.empty:
        return None

    last_close = df["종가"].iloc[-1]
    lookback = df.tail(config.SUPPORT_LOOKBACK)
    recent_low = lookback["저가"].min() if "저가" in df.columns else lookback["종가"].min()
    ma20 = df["MA20"].iloc[-1] if "MA20" in df.columns else np.nan

    candidates = [c for c in (recent_low, ma20) if pd.notna(c) and c < last_close]
    if not candidates:
        return None
    return float(max(candidates))


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
            "buy": [{"ticker": "005930", "rsi": 42.3, ...}, ...],
            "sell": [...]
        }
    """
    all_last_rows = []
    support_map: dict[str, float | None] = {}

    for ticker, df in stock_data.items():
        try:
            analyzed = analyze_stock(df)
            if analyzed.empty:
                continue
            last_row = analyzed.iloc[-1].copy()
            last_row["ticker"] = ticker

            # 골든크로스/데드크로스: 최근 N일 이내 발생 여부로 확장
            recent = analyzed.tail(config.GOLDEN_CROSS_DAYS)
            if recent["골든크로스"].any():
                last_row["골든크로스"] = True
            if recent["데드크로스"].any():
                last_row["데드크로스"] = True

            support_map[ticker] = calculate_support_level(analyzed)
            all_last_rows.append(last_row)
        except Exception:
            continue

    if not all_last_rows:
        return {"buy": [], "sell": []}

    combined = pd.DataFrame(all_last_rows)

    buy_df = filter_buy_candidates(combined)
    sell_df = filter_sell_candidates(combined)

    def to_list(df: pd.DataFrame, include_trade_levels: bool) -> list[dict]:
        records = []
        for _, row in df.iterrows():
            ticker = row["ticker"]
            close = int(row["종가"])
            record = {
                "ticker": ticker,
                "rsi": round(row["RSI"], 1),
                "volume_ratio": round(row["거래량비율"], 1),
                "golden_cross": bool(row.get("골든크로스", False)),
                "dead_cross": bool(row.get("데드크로스", False)),
                "close": close,
            }
            if include_trade_levels:
                support = support_map.get(ticker)
                record["support"] = int(support) if support is not None else None
                record["stop_loss"] = int(round(close * (1 - config.STOP_LOSS_PCT)))
                record["take_profit"] = int(round(close * (1 + config.TAKE_PROFIT_PCT)))
            records.append(record)
        return records

    return {
        "buy": to_list(buy_df, include_trade_levels=True),
        "sell": to_list(sell_df, include_trade_levels=False),
    }
