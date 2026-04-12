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


def get_ticker_name(ticker: str) -> str:
    """종목코드로 종목명 반환."""
    return stock.get_market_ticker_name(ticker)
