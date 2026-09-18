import os
import asyncio
import logging
from typing import Any

import aiohttp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("ksi-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
KSI_API_KEY = os.getenv("KSI_API_KEY", "").strip()

# Put the exact endpoint URLs from your KSI API documentation here
KSI_NUMBERS_ENDPOINT = os.getenv("KSI_NUMBERS_ENDPOINT", "").strip()
KSI_MESSAGES_ENDPOINT = os.getenv("KSI_MESSAGES_ENDPOINT", "").strip()
KSI_EARNINGS_ENDPOINT = os.getenv("KSI_EARNINGS_ENDPOINT", "").strip()

# Optional: if KSI provides an incoming-SMS webhook, use that later.
KSI_WEBHOOK_SECRET = os.getenv("KSI_WEBHOOK_SECRET", "").strip()

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))


def require_config() -> str | None:
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not KSI_API_KEY:
        missing.append("KSI_API_KEY")
    if missing:
        return "Missing environment variable(s): " + ", ".join(missing)
    return None


async def ksi_get(url: str, params: dict[str, Any] | None = None) -> Any:
    if not url:
        raise RuntimeError("KSI endpoint is not configured.")

    headers = {
        # If KSI documentation specifies a different auth header,
        # change this in ONE place.
        "Authorization": f"Bearer {KSI_API_KEY}",
        "Accept": "application/json",
    }

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers, params=params) as r:
            text = await r.text()
            if r.status >= 400:
                raise RuntimeError(f"KSI HTTP {r.status}: {text[:500]}")
            try:
                return await r.json()
            except Exception:
                return {"raw": text}


def pretty_json(data: Any, max_chars: int = 3500) -> str:
    import json
    out = json.dumps(data, ensure_ascii=False, indent=2)
    if len(out) > max_chars:
        out = out[:max_chars] + "\n…"
    return out


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 KSI IPRN Bot\n\n"
        "/numbers - assigned numbers\n"
        "/messages - received SMS records\n"
        "/earnings - earnings statistics\n"
        "/status - configuration status\n\n"
        "API key is kept on the server and is not shown to users."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    missing = require_config()
    if missing:
        await update.message.reply_text("⚠️ " + missing)
        return

    await update.message.reply_text(
        "✅ Bot token: configured\n"
        "✅ KSI API key: configured\n"
        f"{'✅' if KSI_NUMBERS_ENDPOINT else '❌'} Numbers endpoint\n"
        f"{'✅' if KSI_MESSAGES_ENDPOINT else '❌'} Messages endpoint\n"
        f"{'✅' if KSI_EARNINGS_ENDPOINT else '❌'} Earnings endpoint"
    )


async def numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not KSI_NUMBERS_ENDPOINT:
        await update.message.reply_text(
            "⚠️ KSI_NUMBERS_ENDPOINT is not configured yet."
        )
        return
    try:
        data = await ksi_get(KSI_NUMBERS_ENDPOINT)
        await update.message.reply_text("📱 KSI Numbers\n\n" + pretty_json(data))
    except Exception as e:
        log.exception("numbers failed")
        await update.message.reply_text(f"❌ Numbers error: {e}")


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not KSI_MESSAGES_ENDPOINT:
        await update.message.reply_text(
            "⚠️ KSI_MESSAGES_ENDPOINT is not configured yet."
        )
        return
    try:
        data = await ksi_get(KSI_MESSAGES_ENDPOINT)
        await update.message.reply_text("📩 KSI Messages\n\n" + pretty_json(data))
    except Exception as e:
        log.exception("messages failed")
        await update.message.reply_text(f"❌ Messages error: {e}")


async def earnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not KSI_EARNINGS_ENDPOINT:
        await update.message.reply_text(
            "⚠️ KSI_EARNINGS_ENDPOINT is not configured yet."
        )
        return
    try:
        data = await ksi_get(KSI_EARNINGS_ENDPOINT)
        await update.message.reply_text("💰 KSI Earnings\n\n" + pretty_json(data))
    except Exception as e:
        log.exception("earnings failed")
        await update.message.reply_text(f"❌ Earnings error: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled Telegram error", exc_info=context.error)


def main():
    missing = require_config()
    if missing:
        raise SystemExit(missing)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("numbers", numbers))
    app.add_handler(CommandHandler("messages", messages))
    app.add_handler(CommandHandler("earnings", earnings))
    app.add_error_handler(error_handler)

    log.info("KSI Telegram bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
