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
