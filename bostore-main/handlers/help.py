from typing import Union

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
from pyromod.helpers import ikb


@Client.on_callback_query(filters.regex(r"help$"))
async def onhelp_cq(c: Client, cq: CallbackQuery):
    await onhelp_u(c, cq)


@Client.on_message(filters.command("help"))
async def onhelp_m(c: Client, m: Message):
    await onhelp_u(c, m)


async def onhelp_u(c: Client, u: Union[CallbackQuery, Message]):
    lang = u._lang
    is_query = hasattr(u, "data")

    keyb = ikb(
        [
            [("Sobre os produtos", "help_about_products")],
            [("Como comprar", "help_about_buying")],
        ]
    )
    await (u.edit if is_query else u.reply)(lang.help_text, reply_markup=keyb)
