import asyncio
import logging

from pyrogram import idle
from tortoise import run_async

from config import logs_chat, client
from database import connect_database
from waiters import waiters
#

async def alert_startup():
    plugins = [
        (
            handler.user_callback
            if hasattr(handler, "user_callback")
            else handler.callback
        )
        for group in client.dispatcher.groups.values()
        for handler in group
    ]

    plugins_count = len(plugins)

    started_alert = f"""🚀 Bot launched. <code>{plugins_count}</code> plugins loaded.
- <b>app_version</b>: <code>{client.app_version}</code>
- <b>device_model</b>: <code>{client.device_model}</code>
- <b>system_version</b>: <code>{client.system_version}</code>
"""
    await client.send_message(logs_chat, started_alert)


class TelegramHandler(logging.Handler):
    def emit(self, record):
        text = self.format(record)
        asyncio.ensure_future(client.send_message(logs_chat, text))


logger = logging.getLogger()
logger.setLevel(logging.ERROR)
logger.addHandler(TelegramHandler(logging.ERROR))


async def main():
    await client.start()
    waiters.bind_client(client)
    await connect_database()
    await alert_startup()
    print("Running...")
    await idle()


run_async(main())
