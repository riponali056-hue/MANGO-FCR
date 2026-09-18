import os
import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

log = logging.getLogger("ksi-bot")


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
KSI_API_KEY = os.getenv("KSI_API_KEY", "").strip()

KSI_NUMBERS_ENDPOINT = os.getenv(
    "KSI_NUMBERS_ENDPOINT", ""
).strip()

KSI_MESSAGES_ENDPOINT = os.getenv(
    "KSI_MESSAGES_ENDPOINT", ""
).strip()

KSI_EARNINGS_ENDPOINT = os.getenv(
    "KSI_EARNINGS_ENDPOINT", ""
).strip()

REQUEST_TIMEOUT = int(
    os.getenv("REQUEST_TIMEOUT", "20")
)

# Render automatically provides PORT
PORT = int(
    os.getenv("PORT", "10000")
)


# =========================================================
# CONFIG CHECK
# =========================================================

def require_config() -> str | None:

    missing = []

    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if not KSI_API_KEY:
        missing.append("KSI_API_KEY")

    if missing:
        return (
            "Missing environment variable(s): "
            + ", ".join(missing)
        )

    return None


# =========================================================
# KSI API REQUEST
# =========================================================

async def ksi_get(
    url: str,
    params: dict[str, Any] | None = None
) -> Any:

    if not url:
        raise RuntimeError(
            "KSI endpoint is not configured."
        )

    headers = {
        "Authorization": f"Bearer {KSI_API_KEY}",
        "Accept": "application/json",
    }

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        async with session.get(
            url,
            headers=headers,
            params=params
        ) as response:

            response_text = await response.text()

            if response.status >= 400:

                raise RuntimeError(
                    f"KSI HTTP {response.status}: "
                    f"{response_text[:500]}"
                )

            try:
                return await response.json()

            except Exception:

                return {
                    "raw": response_text
                }


# =========================================================
# FORMAT JSON
# =========================================================

def pretty_json(
    data: Any,
    max_chars: int = 3500
) -> str:

    import json

    output = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )

    if len(output) > max_chars:

        output = (
            output[:max_chars]
            + "\n..."
        )

    return output


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🤖 KSI IPRN Bot\n\n"

        "/numbers - Assigned numbers\n"
        "/messages - Received SMS records\n"
        "/earnings - Earnings statistics\n"
        "/status - Bot configuration\n\n"

        "🔐 API key is kept on the server."
    )


# =========================================================
# /STATUS
# =========================================================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    missing = require_config()

    if missing:

        await update.message.reply_text(
            "⚠️ " + missing
        )

        return

    await update.message.reply_text(

        "🤖 KSI Bot Status\n\n"

        "✅ Bot token: configured\n"
        "✅ KSI API key: configured\n"

        f"{'✅' if KSI_NUMBERS_ENDPOINT else '❌'} "
        "Numbers endpoint\n"

        f"{'✅' if KSI_MESSAGES_ENDPOINT else '❌'} "
        "Messages endpoint\n"

        f"{'✅' if KSI_EARNINGS_ENDPOINT else '❌'} "
        "Earnings endpoint"
    )


# =========================================================
# /NUMBERS
# =========================================================

async def get_2_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        result = await ksi_get(NUMBERS_ENDPOINT)

        numbers = result.get("data", [])

        if not numbers:
            await update.message.reply_text(
                "📱 No numbers available right now."
            )
            return

        # শুধুমাত্র প্রথম 2টি number
        numbers = numbers[:2]

        text = "📱 *YOUR NUMBERS*\n"
        text += "━━━━━━━━━━━━━━━━━━\n\n"

        for i, item in enumerate(numbers, 1):
            number = item.get("number", "Unknown")
            range_name = item.get("range_name", "Unknown")

            text += f"{i}️⃣ `{number}`\n"
            text += f"🌍 {range_name}\n\n"

        text += "━━━━━━━━━━━━━━━━━━\n"
        text += f"📊 Showing: {len(numbers)} Numbers"

        keyboard = [
            [
                InlineKeyboardButton(
                    "🔄 Get 2 More Numbers",
                    callback_data="get_2_numbers"
                )
            ]
        ]

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error\n\n{e}"
        )


# =========================================================
# /EARNINGS
# =========================================================

async def earnings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not KSI_EARNINGS_ENDPOINT:

        await update.message.reply_text(
            "⚠️ KSI Earnings endpoint "
            "is not configured."
        )

        return

    try:

        await update.message.reply_text(
            "⏳ Loading earnings..."
        )

        data = await ksi_get(
            KSI_EARNINGS_ENDPOINT
        )

        result = pretty_json(data)

        await update.message.reply_text(

            "💰 KSI Earnings / Statistics\n\n"
            + result
        )

    except Exception as error:

        log.exception(
            "Earnings request failed"
        )

        await update.message.reply_text(

            "❌ Earnings Error\n\n"
            + str(error)
        )


# =========================================================
# RENDER HEALTH SERVER
# =========================================================

async def health(request):

    return web.json_response({

        "ok": True,

        "status": "online",

        "service": "KSI Telegram Bot"

    })


async def run_health_server():

    web_app = web.Application()

    # Root URL
    web_app.router.add_get(
        "/",
        health
    )

    # Health URL
    web_app.router.add_get(
        "/health",
        health
    )

    runner = web.AppRunner(
        web_app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    log.info(
        "Health server listening on 0.0.0.0:%s",
        PORT
    )

    return runner


# =========================================================
# TELEGRAM ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    log.exception(
        "Unhandled Telegram error",
        exc_info=context.error
    )


# =========================================================
# RUN TELEGRAM BOT
# =========================================================

async def run_bot():

    missing = require_config()

    if missing:

        raise RuntimeError(
            missing
        )

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status
        )
    )

    application.add_handler(
        CommandHandler(
            "numbers",
            numbers
        )
    )

    application.add_handler(
        CommandHandler(
            "messages",
            messages
        )
    )

    application.add_handler(
        CommandHandler(
            "earnings",
            earnings
        )
    )

    application.add_error_handler(
        error_handler
    )

    # Start Telegram application

    await application.initialize()

    await application.start()

    await application.updater.start_polling(
        allowed_updates=Update.ALL_TYPES
    )

    log.info(
        "KSI Telegram Bot started successfully"
    )

    try:

        # Keep the bot alive forever

        await asyncio.Event().wait()

    finally:

        log.info(
            "Stopping Telegram bot..."
        )

        await application.updater.stop()

        await application.stop()

        await application.shutdown()


# =========================================================
# MAIN ASYNC
# =========================================================

async def main_async():

    # Start Render HTTP server

    await run_health_server()

    # Start Telegram bot

    await run_bot()


# =========================================================
# MAIN
# =========================================================

def main():

    try:

        asyncio.run(
            main_async()
        )

    except KeyboardInterrupt:

        log.info(
            "Bot stopped manually."
        )


# =========================================================
# START PROGRAM
# =========================================================

if __name__ == "__main__":

    main()
