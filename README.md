# KSI IPRN Telegram Bot

A small Telegram bot starter for connecting to the KSI IPRN REST API.

## Features

- `/numbers` — request assigned-number data
- `/messages` — request received-message history
- `/earnings` — request earnings data
- `/status` — check server configuration

## Important

Do NOT put your Telegram bot token or KSI API key in GitHub.

For Render, add them as Environment Variables.

The exact KSI endpoint URLs and authentication header must match the API documentation shown in your KSI dashboard. This starter uses:

`Authorization: Bearer YOUR_KSI_API_KEY`

If KSI's documentation specifies another header/authentication method, change `ksi_get()` in `bot.py`.

## Local test

```bash
pip install -r requirements.txt
export BOT_TOKEN="..."
export KSI_API_KEY="..."
export KSI_NUMBERS_ENDPOINT="..."
export KSI_MESSAGES_ENDPOINT="..."
export KSI_EARNINGS_ENDPOINT="..."
python bot.py
```

## Render

Create a Web Service from this repository.

Build Command:
`pip install -r requirements.txt`

Start Command:
`python bot.py`

Add the same values under Environment Variables.

For true 24/7 operation, use a paid Render instance or another always-on host; do not rely on a free instance staying continuously active.

## Next integration step

Once the exact KSI endpoint paths and response format are confirmed, the bot can be extended with:

- country/operator menus
- number inventory
- user/sub-client assignment
- incoming SMS notifications
- per-message earnings display
- admin-only commands
- webhook-based SMS delivery
