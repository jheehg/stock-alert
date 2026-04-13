import pandas as pd
from unittest.mock import patch
from collector import filter_by_market_cap, get_ticker_name


def _mock_listing():
    return pd.DataFrame({
        "Code": ["005930", "000660", "999999"],
        "Name": ["삼성전자", "SK하이닉스", "잡주"],
        "Marcap": [400_000_000_000_000, 100_000_000_000_000, 300_000_000_000],
    })


def test_filter_by_market_cap():
    """시가총액 5000억 미만 종목이 필터링되는지 확인"""
    with patch("collector._get_kospi_listing", return_value=_mock_listing()):
        result = filter_by_market_cap("20260410")
        assert "005930" in result
        assert "000660" in result
        assert "999999" not in result


def test_get_ticker_name():
    """종목코드로 종목명을 조회하는지 확인"""
    with patch("collector._get_kospi_listing", return_value=_mock_listing()):
        assert get_ticker_name("005930") == "삼성전자"
        assert get_ticker_name("999999") == "잡주"
