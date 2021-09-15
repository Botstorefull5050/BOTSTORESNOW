import re
import traceback

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyromod.helpers import ikb
from pyromod.listen import listen

from config import admin_chat
from database import Gift, User
from utils import strip_float


@Client.on_callback_query(filters.regex(r"redeem_gifts$"))
async def on_redeem_gifts(c: Client, cq: CallbackQuery):
    lang = cq._lang
    chat = cq.message.chat
    keyb = ikb([[("<<", "start")]])

    try:
        await cq.message.delete()
    except:
        traceback.print_exc()
    last_msg = None
    while True:
        if last_msg:
            await last_msg.request.remove_keyboard()
        try:
            last_msg = msg = await chat.ask(
                lang.ask_gift_card, reply_markup=keyb, timeout=300
            )
        except listen.ListenerCanceled:
            return
        if not msg.text:
            await msg.reply(lang.expecting_text_msg, quote=True)
            continue
        gift_code = re.search(r"(\w{11})", msg.text)
        if not gift_code:
            await msg.reply(lang.gift_card_not_found_to_redeem, quote=True)
            continue
        break
    if last_msg:
        await last_msg.request.remove_keyboard()

    gift_code = gift_code[1]
    gift = await Gift.get_or_none(code=gift_code)
    if not gift:
        return await msg.reply(lang.gift_unexistent)

    # redeem code
    price = strip_float(gift.price)
    user_db = await User.get(id=msg.from_user.id)
    balance = strip_float(user_db.balance + price)
    await user_db.update(balance=balance)
    await Gift.get(code=gift.code).delete()
    await msg.reply(lang.gift_redeemed_alert(price=price, balance=balance), keyb)
    try:
        await msg.delete()
    except:
        traceback.print_exc()

    text = lang.customer_redeemed_alert
    text.escape_html = False
    user = cq.from_user
    mention = (
        f"@{user.username}"
        if user.username
        else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    )
    text = text(
        mention=mention, user_id=user.id, price=price, balance=balance, code=gift_code
    )
    await c.send_message(admin_chat, text)
