import pandas as pd
import numpy as np
from analyzer import calculate_moving_averages, calculate_rsi, calculate_volume_ratio
from analyzer import detect_cross_signals, filter_buy_candidates, filter_sell_candidates
from analyzer import analyze_stock, analyze_all


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


def test_detect_golden_cross():
    """MA5가 MA20을 상향 돌파하면 골든크로스 감지"""
    df = pd.DataFrame({
        "MA5": [95, 98, 101, 103],
        "MA20": [100, 100, 100, 100],
    })
    result = detect_cross_signals(df)
    assert result["골든크로스"].iloc[2] == True
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
    """거래량 120% 미만이면 매수 후보에서 제외"""
    df = pd.DataFrame({
        "골든크로스": [True],
        "RSI": [42.0],
        "거래량비율": [1.1],
    })
    result = filter_buy_candidates(df)
    assert len(result) == 0


def test_filter_sell_candidates():
    """(데드크로스 OR RSI>=70) AND 거래량 120% 이상이면 매도 후보"""
    df = pd.DataFrame({
        "데드크로스": [True, False, False],
        "RSI": [50, 75, 75],
        "거래량비율": [2.0, 1.8, 1.2],
    })
    result = filter_sell_candidates(df)
    assert len(result) == 3  # 전부 거래량 120% 이상


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
    prices = list(range(100, 170))
    volumes = [1000] * 70
    df = make_sample_df(prices, volumes)
    stock_data = {"005930": df}

    result = analyze_all(stock_data)
    assert "buy" in result
    assert "sell" in result
    assert isinstance(result["buy"], list)
    assert isinstance(result["sell"], list)
