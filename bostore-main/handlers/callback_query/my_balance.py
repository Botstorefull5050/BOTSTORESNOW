from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyromod.helpers import ikb

from database import Card, User
from utils import strip_float


@Client.on_callback_query(filters.regex(r"my_balance$"))
async def my_balance(c: Client, cq: CallbackQuery):
    lang = cq._lang
    us = await User.get(id=cq.from_user.id)
    balance = strip_float(us.balance)
    bought_cards = len(await Card.filter(owner=us.id))
    keyb = ikb([[("<<", "start")]])
    text = lang.my_balance_text(
        user_id=us.id,
        balance=balance,
        bought_cards=bought_cards,
    )
    await cq.edit(text, keyb)
