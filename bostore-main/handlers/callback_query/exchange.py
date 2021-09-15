import random
import re
from datetime import datetime, timezone

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyromod.helpers import ikb
from pyromod.listen import listen

from config import admin_chat
from database import User, Card, Cpfs
from utils import (
    get_time_for_exchange,
    atem_check_full,
    strip_float,
    get_random_person,
)
from .buy_cc import prices


@Client.on_callback_query(filters.regex(r"^exchange$"))
async def exchange(c: Client, cq: CallbackQuery):
    lang = cq._lang
    cq.message.chat.cancel_listener()

    user_db = await User.get(id=cq.from_user.id)
    now = datetime.now(timezone.utc)

    cards = await Card.filter(owner=user_db.id)
    eligible = []
    for card in cards:
        time_for_exchange = get_time_for_exchange(card.plan)
        delta = now - card.bought_date
        minutes_passed = delta.total_seconds() / 60
        if minutes_passed < time_for_exchange and not (
            card.plan.lower().startswith("troca")
            or card.plan.lower().startswith("live")
        ):
            eligible.append(card)

    text = lang.exchange_text(total_eligible=len(eligible))
    lines = []
    if eligible:
        lines.append([(lang.start_exchanging, "start_exchanging")])
    lines.append([("<<", "start")])
    keyb = ikb(lines)
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"start_exchanging$"))
async def start_exchanging(c: Client, cq: CallbackQuery):
    lang = cq._lang
    user_db = await User.get(id=cq.from_user.id)
    now = datetime.now(timezone.utc)

    cards = await Card.filter(owner=user_db.id)
    eligible = []
    cards_str = []
    for card in cards:
        time_for_exchange = get_time_for_exchange(card.plan)
        delta = now - card.bought_date
        minutes_passed = delta.total_seconds() / 60
        if minutes_passed < time_for_exchange and not (
            card.plan.lower().startswith("troca")
            or card.plan.lower().startswith("live")
            or card.plan.lower().startswith("die")
        ):
            eligible.append(card)
            date = card.date.replace("/", "|")
            cvv = str(card.cvv).zfill(3)
            cards_str.append(
                f"<code>{card.number}|{date}|{cvv}|{card.level}|{card.card_type}|{card.vendor}|{card.bank}|{card.country}</code>"
            )
    cards_str = "\n".join(cards_str)

    text = lang.exchange_ask
    text.escape_html = False
    text = text(cards_str=cards_str)
    keyb = ikb([[("<<", "exchange")]])
    await cq.edit(text)

    chat = cq.message.chat
    last_msg = None
    while True:
        if last_msg:
            await last_msg.request.remove_keyboard()
        try:
            last_msg = msg = await chat.ask(
                lang.ask_cards_to_exchange, reply_markup=keyb, timeout=300
            )
        except listen.ListenerCanceled:
            return
        if not msg.text:
            await msg.reply(lang.expecting_text_msg, quote=True)
            continue
        cards = [
            *re.finditer(
                r"(?P<number>\d+)\|(?P<date>\d{2}\|\d{2,4})\|(?P<cvv>\d+)", msg.text
            )
        ]
        if not cards:
            await msg.reply(lang.no_card_found_to_exchange, quote=True)
            continue
        break
    if last_msg:
        await last_msg.request.remove_keyboard()

    msg_alert = await msg.reply(lang.exchanging)
    admin_str = []
    for card in cards:
        # print(card)
        old_repr = "|".join(
            [
                card["number"],
                card["date"],
                card["cvv"],
            ]
        )
        # print(old_repr)
        await msg.reply_chat_action("typing")

        card_db = await Card.get_or_none(number=card["number"], cvv=card["cvv"])
        if not card_db or card_db.owner != cq.from_user.id:
            await msg_alert.reply_text(lang.card_unexistent_db(card=old_repr))
            continue
        time_for_exchange = get_time_for_exchange(card_db.plan)
        delta = now - card_db.bought_date
        minutes_passed = delta.total_seconds() / 60
        if minutes_passed > time_for_exchange:
            await msg_alert.reply_text(lang.time_for_exchange_exceeded(card=old_repr))
            continue
        if card_db.plan.startswith("TROCA"):
            await msg_alert.reply_text(lang.double_exchange_unallowed(card=old_repr))
            continue
        elif card_db.plan.startswith("LIVE"):
            await msg_alert.reply_text(lang.double_check_unallowed(card=old_repr))
            continue
        elif card_db.plan.startswith("DIE"):
            continue

        is_live, _, gates = await atem_check_full(card_db)  # check_times=2
        if is_live:
            await msg_alert.reply_text(lang.exchange_live_card(card=old_repr))
            new_plan = "LIVE " + card_db.plan
            await card_db.update(plan=new_plan)
            continue
        else:
            if isinstance(gates, str):
                old_repr += f"|GATE_{gates}"
            else:
                for gate in gates:
                    old_repr += f"|GATE_{gate}"

        level = card_db.level
        if card_db.plan.startswith("BIN"):
            available = await Card.filter(
                card_bin=card_db.plan.split()[1],
                vendor=card_db.vendor,
                owner=None,
                dead=False,
            )
        else:
            available = await Card.filter(level=level.upper(), owner=None, dead=False)

        if not available:
            await msg_alert.reply_text(lang.no_cc_available_to_exchange(card=old_repr))
            continue
        for new_card in available:
            is_live, new_repr, gate = await atem_check_full(new_card)
            if is_live is True:
                if card_db.plan.lower().startswith("unit_full"):
                    # cpfs = await Cpfs.all().filter(owner=None)
                    # rcpf = random.choice(cpfs)
                    # await rcpf.update(
                    #    owner=cq.from_user.id, linked_to_card=new_repr.split("|")[0]
                    # )
                    rcpf = await get_random_person()
                    new_repr += f"|Nome:{rcpf.get('nome')}|CPF:{rcpf.get('cpf')}"
                new_repr += f"|GATE_{gate}"
                break
            if is_live is False:
                await new_card.update(dead=True)
        if not is_live and card_db.plan.startswith("BIN"):
            await msg_alert.reply_text(
                lang.no_cc_available_to_exchange_bin(card=old_repr)
            )
            price = prices["specific"].get(
                str(card_db.card_bin),
                strip_float(prices["unit"][card_db.level.lower()]) + 5,
            )
            user_db = await User.get(id=cq.from_user.id)
            balance = strip_float(user_db.balance + price)
            await user_db.update(balance=balance)
            card_db.update(plan="DIE " + card_db.plan)
            continue
        elif not is_live:
            await msg_alert.reply_text(lang.no_cc_available_to_exchange(card=old_repr))
            continue
        await card_db.update(owner=None, dead=True)
        new_plan = "TROCA " + card_db.plan
        await new_card.update(
            owner=cq.from_user.id, bought_date=datetime.now(timezone.utc), plan=new_plan
        )
        await msg_alert.reply_text(lang.exchange_suceeded(old=old_repr, new=new_repr))
        admin_str.append(f"<s>{old_repr}</s> » <code>{new_repr}</code>")

    keyb = ikb([[("<<", "exchange")]])

    await cq.message.reply(lang.click_back, keyb)

    if not admin_str:
        return

    admin_str = "\n".join(admin_str)
    text = lang.exchange_alert
    text.escape_html = False
    user = cq.from_user
    mention = (
        f"@{user.username}"
        if user.username
        else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    )
    text = text(mention=mention, user_id=user.id, cards_str=admin_str)
    await c.send_message(admin_chat, text)
