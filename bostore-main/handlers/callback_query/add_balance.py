from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyromod.helpers import ikb


@Client.on_callback_query(filters.regex(r"add_balance$"))
async def add_balance(c: Client, cq: CallbackQuery):
    lang = cq._lang
    keyb = ikb([[("🔹 Pix", "lara_pix")], [("<<", "start")]])
    text = lang.add_balance_text
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"lara_(?P<lara>\w+)"))
async def lara_select(c: Client, cq: CallbackQuery):
    lang = cq._lang
    lara = cq.matches[0]["lara"]
    text = lang.lara_inter_info if lara == "inter" else lang.lara_pix_info
    keyb = ikb([[("<<", "add_balance")]])
    await cq.edit(text, keyb)
