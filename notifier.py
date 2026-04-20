import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_MAX_LENGTH = 4096


def format_message(
    candidates: dict[str, list[dict]],
    stats: dict | None = None,
) -> str:
    """매수/매도 후보를 텔레그램 메시지 문자열로 포매팅.

    stats: {"total": int, "failed": int} — 수집 결과 집계 (선택)
    """
    buy = candidates["buy"]
    sell = candidates["sell"]

    lines: list[str] = []
    if stats:
        total = stats.get("total", 0)
        failed = stats.get("failed", 0)
        if total:
            fail_rate = (failed / total) * 100
            lines.append(f"📊 수집 {total - failed}/{total} (실패 {failed}, {fail_rate:.1f}%)")
            lines.append("")

    if not buy and not sell:
        lines.append("오늘은 매수/매도 후보가 없습니다.")
        return "\n".join(lines)

    if buy:
        lines.append(f"📈 매수 후보 ({len(buy)}종목)")
        for i, item in enumerate(buy, 1):
            signals = []
            if item["golden_cross"]:
                signals.append("골든크로스")
            signals.append(f"RSI {item['rsi']}")
            signals.append(f"거래량 {int(item['volume_ratio'] * 100)}%")
            lines.append(f"{i}. {item['name']} ({item['ticker']})")
            lines.append(f"   {' | '.join(signals)} | 종가 {item['close']:,}원")
            support = item.get("support")
            support_str = f"{support:,}원" if support is not None else "N/A"
            lines.append(
                f"   지지선 {support_str} | 손절 {item['stop_loss']:,} | 목표 {item['take_profit']:,}"
            )
        lines.append("")

    if sell:
        lines.append(f"📉 보유 종목 매도 신호 ({len(sell)}종목)")
        for i, item in enumerate(sell, 1):
            signals = []
            if item["dead_cross"]:
                signals.append("데드크로스")
            if item["rsi"] >= 70:
                signals.append(f"RSI {item['rsi']}")
            signals.append(f"거래량 {int(item['volume_ratio'] * 100)}%")
            lines.append(f"{i}. {item['name']} ({item['ticker']})")
            lines.append(f"   {' | '.join(signals)} | 종가 {item['close']:,}원")

    return "\n".join(lines)


def split_message(message: str) -> list[str]:
    """텔레그램 글자 제한(4096자)에 맞게 메시지를 줄 단위로 분할."""
    if len(message) <= TELEGRAM_MAX_LENGTH:
        return [message]

    chunks = []
    current = ""
    for line in message.split("\n"):
        if len(current) + len(line) + 1 > TELEGRAM_MAX_LENGTH:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


async def _send_telegram(message: str) -> None:
    """텔레그램 메시지 발송 (내부용)."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    chunks = split_message(message)
    for chunk in chunks:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk)


def send_alert(candidates: dict[str, list[dict]], stats: dict | None = None) -> None:
    """매수/매도 후보를 텔레그램으로 발송. 실패 시 1회 재시도."""
    message = format_message(candidates, stats=stats)
    for attempt in range(2):
        try:
            asyncio.run(_send_telegram(message))
            return
        except Exception as e:
            if attempt == 0:
                continue
            raise RuntimeError(f"텔레그램 발송 실패: {e}")


def send_error(error_msg: str) -> None:
    """에러 메시지를 텔레그램으로 발송."""
    try:
        asyncio.run(_send_telegram(f"⚠️ Stock Alert 오류\n{error_msg}"))
    except Exception:
        pass
