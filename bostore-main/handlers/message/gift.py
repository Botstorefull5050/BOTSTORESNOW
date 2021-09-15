import random
import re
import string
import traceback

from pyrogram import Client, filters
from pyrogram.types import Message

from config import admins, gifters, admin_chat
from database import Gift, User


def id_generator(size=11, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


async def generate_new_gift(price):
    code = id_generator()
    exists = await Gift.get_or_none(code=code)
    if exists:
        while exists:
            code = id_generator()
            exists = await Gift.get_or_none(code=code)
    await Gift.create(price=price, code=code)
    return code


@Client.on_message(filters.regex(r"/gift(?: (?P<arg>.+))"))
async def on_gift(c: Client, m: Message):
    lang = m._lang
    arg = m.matches[0]["arg"]

    if not arg:
        return await m.reply(lang.gift_user_usage)

    if await filters.user(admins + gifters)(c, m):
        is_price = re.match(r"-?\d(\.?\d{,10})?$", arg)
        if is_price:
            price = float(arg)
            decimals = price % 1
            if decimals < 0.1:
                price = int(price)

            code = await generate_new_gift(price)
            await m.reply(lang.gift_created(price=price, code=code))
            text = f"🎁 {m.from_user.first_name} criou um gift card de <b>R${price}</b>\n- Gift card: <code>{code}</code>"
            await c.send_message(admin_chat, text)
            return

    gift = await Gift.get_or_none(code=arg)
    if not gift:
        return await m.reply(lang.gift_unexistent)

    # redeem code
    price = gift.price
    decimals = price % 1
    if decimals < 0.1:
        price = int(price)
    user_db = await User.get(id=m.from_user.id)
    balance = user_db.balance + price
    decimals = balance % 1
    if decimals < 0.1:
        balance = int(balance)
    await user_db.update(balance=balance)
    await Gift.get(code=gift.code).delete()
    await m.reply(lang.gift_redeemed_alert(price=price, balance=balance))
    try:
        await m.delete()
    except:
        traceback.print_exc()

    text = lang.customer_redeemed_alert
    text.escape_html = False
    user = m.from_user
    mention = (
        f"@{user.username}"
        if user.username
        else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    )
    text = text(
        mention=mention, user_id=user.id, price=price, balance=balance, code=arg
    )
    await c.send_message(admin_chat, text)
