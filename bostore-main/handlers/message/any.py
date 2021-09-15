import re

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
from pyromod.helpers import ikb

from config import langs
from database import User
from ..start import onstart_u


# Getting the language to use
@Client.on_message(group=-2)
async def deflang(client, message):
    language = "en"
    from_user = message.from_user
    if not from_user:
        message._lang = langs.get_language(language)
        return
    language = langs.normalize_code(from_user.language_code or "en")
    if message.chat.type == "private":
        user, _ = await User.get_or_create({"language": language}, id=from_user.id)
        language = user.language
    message._lang = langs.get_language(language)
    await alert_agreed_tos(client, message)


# Define what updates to reject
@Client.on_message(~filters.private | filters.edited)
async def reject(client, message):
    if message.chat.type != "private" and message.chat.id != -1001520909324:
        await message.chat.leave()
    message.stop_propagation()


async def alert_agreed_tos(c: Client, m: Message):
    lang = m._lang
    user_db = await User.get(id=m.from_user.id)
    if user_db.agreed_tos:
        return

    is_ref = re.match(r"/start ref(?P<id>\d+)", m.text)
    if is_ref:
        await user_db.update(referrer=int(is_ref["id"]))

    text = lang.ask_agreed_tos
    keyb = ikb([[(lang.agreed, "agreed_tos")]])
    await m.reply(text, keyb)
    m.stop_propagation()


@Client.on_callback_query(filters.regex(r"^agreed_tos$"))
async def on_agreed_tos(c: Client, cq: CallbackQuery):
    user_db = await User.get(id=cq.from_user.id)
    await user_db.update(agreed_tos=True)
    await onstart_u(c, cq)
