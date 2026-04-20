import pandas as pd
from unittest.mock import patch
from collector import filter_by_market_cap, get_ticker_name


def _mock_listing():
    return pd.DataFrame({
        "Code": ["005930", "000660", "999999", "035720", "111111"],
        "Name": ["삼성전자", "SK하이닉스", "잡주", "카카오닥", "잡닥"],
        "Marcap": [
            400_000_000_000_000,  # KOSPI 대형
            100_000_000_000_000,  # KOSPI 대형
            300_000_000_000,      # KOSPI 소형 (1조 미만 → 제외)
            800_000_000_000,      # KOSDAQ 중형 (5000억 이상 → 포함)
            100_000_000_000,      # KOSDAQ 소형 (5000억 미만 → 제외)
        ],
        "Market": ["KOSPI", "KOSPI", "KOSPI", "KOSDAQ", "KOSDAQ"],
    })


def test_filter_by_market_cap():
    """KOSPI 1조↑, KOSDAQ 5000억↑ 기준 필터링 확인"""
    with patch("collector._get_listing", return_value=_mock_listing()):
        result = filter_by_market_cap("20260410")
        assert "005930" in result
        assert "000660" in result
        assert "035720" in result   # KOSDAQ 5000억 이상
        assert "999999" not in result  # KOSPI 1조 미만
        assert "111111" not in result  # KOSDAQ 5000억 미만


def test_get_ticker_name():
    """종목코드로 종목명을 조회하는지 확인"""
    with patch("collector._get_listing", return_value=_mock_listing()):
        assert get_ticker_name("005930") == "삼성전자"
        assert get_ticker_name("035720") == "카카오닥"
