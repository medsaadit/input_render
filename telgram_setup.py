from telethon.sync import TelegramClient  # Telegram API client
import asyncio  # Async IO operations

API_ID = 20445291 
API_HASH = 'f85a52ec518d7d9376ab3b99b5fd3fc5'  

TARGET_CHAT_ID = -1002670598744  # Commented out alternative chat ID
with TelegramClient('telegram_session', API_ID, API_HASH) as client:
    client.send_message(TARGET_CHAT_ID, 'Bot is ready!')
    print("Message sent successfully")
