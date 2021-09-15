from typing import Union

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
from pyromod.helpers import ikb

from config import admins


@Client.on_message(filters.regex(r"/painel") & filters.user(admins))
async def on_panel_m(c: Client, m: Message):
    await on_panel_u(c, m)


@Client.on_callback_query(filters.regex(r"panel") & filters.user(admins))
async def on_panel_cq(c: Client, cq: CallbackQuery):
    await on_panel_u(c, cq)


async def on_panel_u(c: Client, u: Union[CallbackQuery, Message]):
    lang = u._lang
    is_query = hasattr(u, "data")

    keyb = ikb(
        [
            [(lang.customers, "customers"), (lang.stats, "stats")],
            [(lang.broadcast, "broadcast")],
        ]
    )
    text = lang.panel_text
    await (u.edit if is_query else u.reply)(text, keyb)
