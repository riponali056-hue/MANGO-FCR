import os
import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import web

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
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

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    ""
).strip()

KSI_API_KEY = os.getenv(
    "KSI_API_KEY",
    ""
).strip()

KSI_NUMBERS_ENDPOINT = os.getenv(
    "KSI_NUMBERS_ENDPOINT",
    ""
).strip()

KSI_MESSAGES_ENDPOINT = os.getenv(
    "KSI_MESSAGES_ENDPOINT",
    ""
).strip()

KSI_EARNINGS_ENDPOINT = os.getenv(
    "KSI_EARNINGS_ENDPOINT",
    ""
).strip()

REQUEST_TIMEOUT = int(
    os.getenv(
        "REQUEST_TIMEOUT",
        "20"
    )
)

# Render automatically provides PORT
PORT = int(
    os.getenv(
        "PORT",
        "10000"
    )
)


# =========================================================
# CONFIG CHECK
# =========================================================

def require_config() -> str | None:

    missing = []

    if not BOT_TOKEN:
        missing.append(
            "BOT_TOKEN"
        )

    if not KSI_API_KEY:
        missing.append(
            "KSI_API_KEY"
        )

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
        "Authorization": (
            f"Bearer {KSI_API_KEY}"
        ),
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

            response_text = (
                await response.text()
            )

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
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [

        [
            InlineKeyboardButton(
                "📱 Get 2 Numbers",
                callback_data="get_2_numbers:1"
            )
        ]

    ]

    reply_markup = (
        InlineKeyboardMarkup(
            keyboard
        )
    )

    await update.message.reply_text(

        "🤖 KSI IPRN Bot\n\n"

        "📱 Get numbers 2 at a time.\n\n"

        "/numbers - All assigned numbers\n"
        "/messages - Received SMS records\n"
        "/earnings - Earnings statistics\n"
        "/status - Bot configuration\n\n"

        "🔐 API key is kept on the server.",

        reply_markup=reply_markup
    )


# =========================================================
# STATUS
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

async def numbers(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not KSI_NUMBERS_ENDPOINT:

        await update.message.reply_text(
            "⚠️ KSI Numbers endpoint "
            "is not configured."
        )

        return

    try:

        await update.message.reply_text(
            "⏳ Loading numbers..."
        )

        data = await ksi_get(
            KSI_NUMBERS_ENDPOINT
        )

        result = pretty_json(
            data
        )

        await update.message.reply_text(

            "📱 KSI Numbers\n\n"
            + result
        )

    except Exception as error:

        log.exception(
            "Numbers request failed"
        )

        await update.message.reply_text(

            "❌ Numbers Error\n\n"
            + str(error)
        )


# =========================================================
# GET 2 NUMBERS
# =========================================================

async def get_2_numbers(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 1
):

    if not KSI_NUMBERS_ENDPOINT:

        if update.message:

            await update.message.reply_text(
                "⚠️ KSI Numbers endpoint "
                "is not configured."
            )

        elif update.callback_query:

            await update.callback_query.message.reply_text(
                "⚠️ KSI Numbers endpoint "
                "is not configured."
            )

        return

    try:

        # Request only 2 numbers from KSI
        params = {
            "page": page,
            "per_page": 2
        }

        result = await ksi_get(
            KSI_NUMBERS_ENDPOINT,
            params=params
        )

        numbers_list = result.get(
            "data",
            []
        )

        pagination = result.get(
            "pagination",
            {}
        )

        total = pagination.get(
            "total",
            0
        )

        current_page = pagination.get(
            "current_page",
            page
        )

        last_page = pagination.get(
            "last_page",
            page
        )

        # -------------------------------------------------
        # No numbers
        # -------------------------------------------------

        if not numbers_list:

            text = (
                "📱 *NO MORE NUMBERS*\n\n"
                "There are no more numbers "
                "available right now."
            )

            if update.callback_query:

                await update.callback_query.message.edit_text(
                    text,
                    parse_mode="Markdown"
                )

            else:

                await update.message.reply_text(
                    text,
                    parse_mode="Markdown"
                )

            return

        # -------------------------------------------------
        # Build message
        # -------------------------------------------------

        text = (
            "📱 *YOUR NUMBERS*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

        for i, item in enumerate(
            numbers_list,
            1
        ):

            number = item.get(
                "number",
                "Unknown"
            )

            range_name = item.get(
                "range_name",
                "Unknown"
            )

            text += (
                f"{i}️⃣ `{number}`\n"
            )

            text += (
                f"🌍 {range_name}\n\n"
            )

        text += (
            "━━━━━━━━━━━━━━━━━━\n"
        )

        text += (
            f"📊 Showing: "
            f"{len(numbers_list)} Numbers\n"
        )

        if total:

            text += (
                f"📦 Total: {total}\n"
            )

        text += (
            f"📄 Page: "
            f"{current_page}/{last_page}"
        )

        # -------------------------------------------------
        # Next button
        # -------------------------------------------------

        keyboard = []

        if current_page < last_page:

            keyboard.append(
                [
                    InlineKeyboardButton(
                        "🔄 Change Number",
                        callback_data=(
                            f"get_2_numbers:"
                            f"{current_page + 1}"
                        )
                    )
                ]
            )

        else:

            text += (
                "\n\n✅ You reached the "
                "last page."
            )

        # -------------------------------------------------
        # Reply
        # -------------------------------------------------

        reply_markup = None

        if keyboard:

            reply_markup = (
                InlineKeyboardMarkup(
                    keyboard
                )
            )

        if update.callback_query:

            await update.callback_query.message.edit_text(

                text,

                parse_mode="Markdown",

                reply_markup=reply_markup
            )

        else:

            await update.message.reply_text(

                text,

                parse_mode="Markdown",

                reply_markup=reply_markup
            )

    except Exception as error:

        log.exception(
            "Get 2 numbers failed"
        )

        error_text = (
            "❌ Get Numbers Error\n\n"
            + str(error)
        )

        if update.callback_query:

            await update.callback_query.message.reply_text(
                error_text
            )

        else:

            await update.message.reply_text(
                error_text
            )


# =========================================================
# GET 2 NUMBERS CALLBACK
# =========================================================

async def get_2_numbers_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    # callback_data format:
    # get_2_numbers:1
    # get_2_numbers:2
    # get_2_numbers:3

    try:

        page = int(
            query.data.split(
                ":"
            )[1]
        )

    except Exception:

        page = 1

    await get_2_numbers(
        update,
        context,
        page=page
    )


# =========================================================
# /MESSAGES
# =========================================================

async def messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not KSI_MESSAGES_ENDPOINT:

        await update.message.reply_text(
            "⚠️ KSI Messages endpoint "
            "is not configured."
        )

        return

    try:

        await update.message.reply_text(
            "⏳ Loading messages..."
        )

        data = await ksi_get(
            KSI_MESSAGES_ENDPOINT
        )

        result = pretty_json(
            data
        )

        await update.message.reply_text(

            "📩 KSI Messages\n\n"
            + result
        )

    except Exception as error:

        log.exception(
            "Messages request failed"
        )

        await update.message.reply_text(

            "❌ Messages Error\n\n"
            + str(error)
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

        result = pretty_json(
            data
        )

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

async def health(
    request
):

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
        "Health server listening "
        "on 0.0.0.0:%s",
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

    # -----------------------------------------------------
    # Commands
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Get 2 Numbers Button
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            get_2_numbers_callback,
            pattern=r"^get_2_numbers:\d+$"
        )
    )

    # -----------------------------------------------------
    # Telegram Error Handler
    # -----------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    # -----------------------------------------------------
    # Start Telegram application
    # -----------------------------------------------------

    await application.initialize()

    await application.start()

    await application.updater.start_polling(
        allowed_updates=Update.ALL_TYPES
    )

    log.info(
        "KSI Telegram Bot started successfully"
    )

    try:

        # Keep bot alive forever

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
