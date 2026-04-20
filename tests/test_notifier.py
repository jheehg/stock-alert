from notifier import format_message, split_message, TELEGRAM_MAX_LENGTH


def test_format_message_with_candidates():
    """매수/매도 후보가 있을 때 메시지 포맷 확인"""
    candidates = {
        "buy": [
            {"ticker": "005930", "name": "삼성전자", "rsi": 42.3, "volume_ratio": 2.3,
             "golden_cross": True, "dead_cross": False, "close": 71000,
             "support": 69000, "stop_loss": 68870, "take_profit": 75260},
        ],
        "sell": [
            {"ticker": "000660", "name": "SK하이닉스", "rsi": 75.2, "volume_ratio": 1.8,
             "golden_cross": False, "dead_cross": False, "close": 150000},
        ],
    }
    result = format_message(candidates)
    assert "매수 후보" in result
    assert "삼성전자" in result
    assert "매도 후보" in result
    assert "SK하이닉스" in result


def test_format_message_empty():
    """후보가 없을 때 메시지 확인"""
    candidates = {"buy": [], "sell": []}
    result = format_message(candidates)
    assert "후보가 없습니다" in result


def test_split_message_short():
    """짧은 메시지는 분할하지 않음"""
    msg = "짧은 메시지"
    result = split_message(msg)
    assert result == [msg]


def test_split_message_long():
    """긴 메시지는 4096자 기준으로 분할"""
    msg = "테스트 라인\n" * 1000
    result = split_message(msg)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= TELEGRAM_MAX_LENGTH
