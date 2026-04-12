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


def test_calculate_volume_ratio():
    """거래량 비율이 올바르게 계산되는지 확인"""
    volumes = [1000] * 25 + [3000]  # 마지막날 거래량 3배
    prices = [100] * 26
    df = make_sample_df(prices, volumes)

    result = calculate_volume_ratio(df)
    assert "거래량비율" in result.columns
    # 마지막날: 3000 / mean(1000*20) = 3.0
    assert abs(result["거래량비율"].iloc[-1] - 3.0) < 0.01
