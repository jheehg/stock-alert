# main.py
import sys
from datetime import datetime

import holidays

from collector import filter_by_market_cap, collect_stock_data, get_ticker_name
from analyzer import analyze_all
from notifier import send_alert, send_error


def is_korean_holiday(date: datetime) -> bool:
    """한국 공휴일 여부 확인."""
    kr_holidays = holidays.KR(years=date.year)
    return date.date() in kr_holidays


def main() -> None:
    today = datetime.now()

    # 주말/공휴일 체크
    if today.weekday() >= 5:
        print("오늘은 주말입니다. 종료합니다.")
        return

    if is_korean_holiday(today):
        print("오늘은 공휴일입니다. 종료합니다.")
        return

    today_str = today.strftime("%Y%m%d")
    print(f"[{today_str}] Stock Alert 시작")

    try:
        # 1. 데이터 수집
        print("시가총액 필터링 중...")
        tickers = filter_by_market_cap(today_str)
        if not tickers:
            send_error("시가총액 필터링 결과 종목이 없습니다.")
            return
        print(f"대상 종목: {len(tickers)}개")

        print("일봉 데이터 수집 중...")
        stock_data = collect_stock_data(tickers, today_str)
        if not stock_data:
            send_error("일봉 데이터 수집에 실패했습니다.")
            return
        print(f"수집 완료: {len(stock_data)}개")

        # 2. 분석
        print("분석 중...")
        candidates = analyze_all(stock_data)

        # 종목명 추가
        for category in ["buy", "sell"]:
            for item in candidates[category]:
                item["name"] = get_ticker_name(item["ticker"])

        print(f"매수 후보: {len(candidates['buy'])}개, 매도 후보: {len(candidates['sell'])}개")

        # 3. 텔레그램 발송
        print("텔레그램 발송 중...")
        send_alert(candidates)
        print("완료!")

    except Exception as e:
        print(f"오류 발생: {e}")
        send_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
