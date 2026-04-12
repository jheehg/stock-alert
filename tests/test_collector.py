import pandas as pd
from unittest.mock import patch, MagicMock
from collector import filter_by_market_cap


def test_filter_by_market_cap():
    """시가총액 5000억 미만 종목이 필터링되는지 확인"""
    with patch("collector.stock.get_market_cap_by_date") as mock_get_cap:
        mock_get_cap.return_value = pd.DataFrame(
            {"시가총액": [400_000_000_000_000, 100_000_000_000_000, 300_000_000_000]},
            index=["005930", "000660", "999999"],
        )
        result = filter_by_market_cap("20260410")
        assert "005930" in result
        assert "000660" in result
        assert "999999" not in result


def test_get_ticker_name():
    """종목코드로 종목명을 조회하는지 확인"""
    with patch("collector.stock.get_market_ticker_name") as mock_name:
        mock_name.return_value = "삼성전자"
        from collector import get_ticker_name
        assert get_ticker_name("005930") == "삼성전자"
