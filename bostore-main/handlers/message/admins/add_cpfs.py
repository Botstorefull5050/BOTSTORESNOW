import os
import re

from pyrogram import Client, filters
from pyrogram.types import Message
from pyromod.helpers import force_reply

from config import admins
from database import Cpfs


async def iter_add_cpfs(cpfs, u):
    lang = u._lang
    total = 0
    success = 0
    for row in re.finditer(r"(?P<cpf>\d{11})", cpfs):
        total += 1
        cpf = row["cpf"]
        info = await is_cpf_valid(cpf)
        if info:
            if not await Cpfs.get_or_none(number=row["cpf"]):
                await Cpfs.create(number=row["cpf"])
                success += 1
            else:
                print(row.group())
    return (
        lang.cpfs_added_alert(total=total, success=success, error=total - success),
        total,
        success,
    )


async def is_cpf_valid(cpf: str) -> bool:
    slice1, slice2 = str(sum(int(i) for i in cpf))
    return slice1 == slice2


@Client.on_message(
    filters.regex(r"/addcpfs( (?P<cpfs>.+))?", re.S) & filters.user(admins)
)
async def on_add_m(c: Client, m: Message):
    await m.reply_chat_action("typing")
    await on_add_u(c, m)


async def on_add_u(c: Client, u: Message):
    lang = u._lang
    is_query = hasattr(u, "data")
    cpfs = u.matches[0]["cpfs"]

    print(cpfs)

    if cpfs:
        text, total, _ = await iter_add_cpfs(cpfs, u)
        if not total:
            text = lang.could_not_find_cpfs
        return await u.reply(text, quote=True)

    await u.reply(lang.in_add_mode_cpfs_alert)

    first = True
    while True:
        chat = u.message.chat if is_query else u.chat
        text = lang.ask_first_send_cpfs if first else lang.ask_send_cpfs
        first = False
        msg = await chat.ask(text, reply_markup=force_reply())
        if not msg.text and (
            not msg.document or msg.document.file_size > 100 * 1024 * 1024
        ):  # 100MB
            await msg.reply(lang.expecting_text_msg_or_document, quote=True)
            continue
        if msg.text and msg.text.startswith("/done"):
            break
        msg._lang = lang

        if msg.document:
            cache = await msg.download()
            with open(cache) as f:
                msg.text = f.read()
            os.remove(cache)

        text, total, _ = await iter_add_cpfs(msg.text, msg)
        if not total:
            text = lang.could_not_find_cpfs
        await msg.reply(text, quote=True)

    await u.reply(lang.out_add_mode_alert)
