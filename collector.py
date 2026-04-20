# collector.py
from datetime import datetime, timedelta

import pandas as pd
import FinanceDataReader as fdr
from pykrx import stock

import config


# 종목 리스트 캐시 (실행당 1회만 조회)
_listing_cache: pd.DataFrame | None = None


def _get_listing() -> pd.DataFrame:
    """코스피 + 코스닥 종목 리스트 조회 (캐시).

    Market 컬럼(KOSPI / KOSDAQ)을 포함한다.
    """
    global _listing_cache
    if _listing_cache is not None:
        return _listing_cache

    kospi = fdr.StockListing("KOSPI").copy()
    kospi["Market"] = "KOSPI"
    kosdaq = fdr.StockListing("KOSDAQ").copy()
    kosdaq["Market"] = "KOSDAQ"

    _listing_cache = pd.concat([kospi, kosdaq], ignore_index=True)
    return _listing_cache


def filter_by_market_cap(date: str) -> list[str]:
    """시장별 시가총액 기준 이상 종목코드 리스트 반환.

    KOSPI: config.MARKET_CAP_KOSPI 이상
    KOSDAQ: config.MARKET_CAP_KOSDAQ 이상

    Args:
        date: "YYYYMMDD" 형식 날짜 (미사용, 인터페이스 유지)

    Returns:
        종목코드 리스트 (예: ["005930", "000660", ...])
    """
    df = _get_listing()
    if df.empty:
        return []

    kospi_mask = (df["Market"] == "KOSPI") & (df["Marcap"] >= config.MARKET_CAP_KOSPI)
    kosdaq_mask = (df["Market"] == "KOSDAQ") & (df["Marcap"] >= config.MARKET_CAP_KOSDAQ)
    filtered = df[kospi_mask | kosdaq_mask]
    return filtered["Code"].tolist()


def collect_stock_data(
    tickers: list[str], end_date: str
) -> tuple[dict[str, pd.DataFrame], int]:
    """종목별 일봉 데이터 수집.

    Args:
        tickers: 종목코드 리스트
        end_date: "YYYYMMDD" 형식 마지막 날짜

    Returns:
        (종목 데이터 딕셔너리, 실패 종목 수)
    """
    start_date = (
        datetime.strptime(end_date, "%Y%m%d") - timedelta(days=config.DATA_DAYS)
    ).strftime("%Y%m%d")

    result: dict[str, pd.DataFrame] = {}
    failed = 0
    for ticker in tickers:
        try:
            df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
            if df.empty:
                failed += 1
                continue
            result[ticker] = df
        except Exception:
            failed += 1
            continue
    return result, failed


def get_ticker_name(ticker: str) -> str:
    """종목코드로 종목명 반환."""
    df = _get_listing()
    match = df[df["Code"] == ticker]
    if not match.empty:
        return match.iloc[0]["Name"]
    return ticker
