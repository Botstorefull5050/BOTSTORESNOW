import asyncio
import html
import re

from pyrogram import Client, filters
from pyrogram.types import Message

from config import sudoers


@Client.on_message(filters.regex(r"^/cmd\s+(?P<code>.+)", re.S) & filters.user(sudoers))
async def cmd(client: Client, message: Message):
    lang = message._lang
    code = message.text.split(maxsplit=1)[1]
    process = await asyncio.create_subprocess_shell(
        code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    result = await process.communicate()
    output = result[0].decode().rstrip() or lang.executed_cmd
    output = html.escape(output)  # escape html special chars
    text = ""
    for line in output.splitlines():
        text += f"<code>{line}</code>\n"
    await message.reply(text)
