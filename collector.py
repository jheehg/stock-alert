# collector.py
from datetime import datetime, timedelta

import pandas as pd
import FinanceDataReader as fdr
from pykrx import stock

import config


# 종목 리스트 캐시 (실행당 1회만 조회)
_listing_cache = None


def _get_kospi_listing() -> pd.DataFrame:
    """코스피 종목 리스트 조회 (캐시)."""
    global _listing_cache
    if _listing_cache is None:
        _listing_cache = fdr.StockListing("KOSPI")
    return _listing_cache


def filter_by_market_cap(date: str) -> list[str]:
    """시가총액 기준 이상 종목코드 리스트 반환.

    Args:
        date: "YYYYMMDD" 형식 날짜 (미사용, 인터페이스 유지)

    Returns:
        종목코드 리스트 (예: ["005930", "000660", ...])
    """
    df = _get_kospi_listing()
    if df.empty:
        return []
    filtered = df[df["Marcap"] >= config.MARKET_CAP_MIN]
    return filtered["Code"].tolist()


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
    df = _get_kospi_listing()
    match = df[df["Code"] == ticker]
    if not match.empty:
        return match.iloc[0]["Name"]
    return ticker
