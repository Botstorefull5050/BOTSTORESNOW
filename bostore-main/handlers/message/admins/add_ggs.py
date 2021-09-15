import os
import re

from pyrogram import Client, filters
from pyrogram.types import Message
from pyromod.helpers import force_reply

from config import admins
from database import Card
from utils import search_bin


async def iter_add_cards(cards, u):
    lang = u._lang
    total = 0
    success = 0
    for row in re.finditer(
        r"(?P<number>\d{16})\W+(?P<month>\d{1,2})\W+(?P<year>\d{2,4})\W+(?P<cvv>\d+)",
        cards,
    ):
        total += 1
        card_bin = row["number"][:6]
        info = await search_bin(card_bin)
        print(info)
        if info:
            date = row["month"].zfill(2) + "/" + row["year"]
            row_values = dict(
                number=row["number"],
                date=date,
                cvv=row["cvv"].zfill(3),
                country=info["country"],
                vendor=info["vendor"],
                card_type=info["card_type"],
                level=info["level"],
                bank=info["bank"],
                card_bin=info["card_bin"],
            )
            if not await Card.get_or_none(number=row["number"], cvv=row["cvv"]):
                await Card.create(**row_values)
                success += 1
            else:
                print(row.group())
    return (
        lang.cards_added_alert(total=total, success=success, error=total - success),
        total,
        success,
    )


@Client.on_message(filters.regex(r"/add( (?P<cards>.+))?", re.S) & filters.user(admins))
async def on_add_m(c: Client, m: Message):
    await m.reply_chat_action("typing")
    await on_add_u(c, m)


async def on_add_u(c: Client, u: Message):
    lang = u._lang
    is_query = hasattr(u, "data")
    cards = u.matches[0]["cards"]

    if cards:
        text, total, _ = await iter_add_cards(cards, u)
        if not total:
            text = lang.could_not_find_cards
        return await u.reply(text, quote=True)

    await u.reply(lang.in_add_mode_alert)

    first = True
    while True:
        chat = u.message.chat if is_query else u.chat
        text = lang.ask_first_send_cards if first else lang.ask_send_cards
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

        text, total, _ = await iter_add_cards(msg.text, msg)
        if not total:
            text = lang.could_not_find_cards
        await msg.reply(text, quote=True)

    await u.reply(lang.out_add_mode_alert)
