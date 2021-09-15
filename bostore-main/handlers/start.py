from typing import Union

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
from pyromod.helpers import ikb

from database import User


@Client.on_callback_query(filters.regex(r"^start"))
async def onstart_cq(c: Client, cq: CallbackQuery):
    await onstart_u(c, cq)


@Client.on_message(filters.command("start"))
async def onstart_m(c: Client, m: Message):
    await onstart_u(c, m)


async def onstart_u(c: Client, u: Union[CallbackQuery, Message]):
    lang = u._lang
    is_query = hasattr(u, "data")
    chat = u.message.chat if is_query else u.chat
    chat.cancel_listener()
    from_user = u.from_user
    user_db = await User.get(id=from_user.id)
    balance = user_db.balance
    decimals = balance % 1
    if decimals < 0.1:
        balance = int(balance)

    text = lang.start_text + lang.wallet_info(balance=balance, user_id=from_user.id)
    keyboard = ikb(
        [
            [(lang.buy_cc, "buy_cc")],
            #[("🔎 chk de InfoCCs", "cc_chk")],
            [(lang.my_balance, "my_balance")],
            [(lang.add_balance, "add_balance")],
            [(lang.redeem_gifts, "redeem_gifts")],
            [(lang.exchange, "exchange")],
        ]
    )

    await (u.edit if is_query else u.reply)(text, keyboard)
