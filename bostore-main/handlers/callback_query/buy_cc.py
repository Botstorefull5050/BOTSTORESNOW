import os
import random
import re
import traceback
from datetime import datetime, timezone

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyromod.helpers import ikb, array_chunk
from pyromod.listen import listen

from config import admin_chat, admins
from database import Card, User, Cpfs
from utils import (
    strip_float,
    atem_check_full,
    ruby_check_full,
    get_time_for_exchange,
    search_bin,
    pretty_time_delta,
    get_random_person,
)

prices = {
    "unit": {
        "electronic": 5,
        "prepaid": 5,
        "basic": 5,
        "basico": 5,
        "classic": 5,
        "electron": 5,
        "personal": 5,
        "standard": 5,
        "gold": 5,
        "elo": 5,
		"elo more": 5,
        "empresarial": 10,
        "platinum": 25,
        "prepaid business": 5,
        "business": 10,
        "executive": 25,
        "corporate": 10,
        "corporate t&e": 10,
        "black": 25,
        "infinite": 40,
},
    "mix": {
        "5": 35,
        "10": 70,
        "20": 140,
        "30": 210,
        "50": 350,
        "100": 700,
        "200": 1400,
        "300": 2100,
        "500": 2500,
        "1000": 3500,
        #"1": 20,
        #"3": 55,
        #"5": 85,
        #"10": 150,
        #"50": 500,
        #"100": 900,
        #"200": 1550,
        #"300": 2100,
        #"500": 3000,
        #"1000": 4800,
    },
    "specific": {
        "516220": 10,
        "523421": 10,
        "550209": 10,
        "516230": 12,
        "516292": 12,
        "230744": 30,
        "530033": 30,
		"650485": 25,
    },
}

@Client.on_callback_query(filters.regex(r"^buy_cc$"))
async def on_buy_cc(c: Client, cq: CallbackQuery):
    lang = cq._lang
    cq.message.chat.cancel_listener()
    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)
    keyb = ikb(
        [
            [(lang.cc_unit, "buy_cc_unit"), (lang.cc_mix, "buy_cc_mix")],
            [(lang.bin_unit, "buy_bin_unit")],
            [("<<", "start")],
        ]
    )
    text = lang.buy_cc_text + lang.wallet_info(balance=balance, user_id=cq.from_user.id)
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^buy_cc_unit$"))
async def on_buy_cc_unit(c: Client, cq: CallbackQuery):
    lang = cq._lang
    products = []
    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)
    for level, price in prices["unit"].items():
        price = strip_float(price)
        products.append(
            (
                f"{level.replace('platinum/world/standard', 'plat/world/stand').title()} — R${price}",
                "unit " + level,
            )
        )
    lines = array_chunk(products, 2)
    lines.append([("<<", "buy_cc")])
    keyb = ikb(lines)

    text = lang.buy_cc_unit_text + lang.wallet_info(
        balance=balance, user_id=cq.from_user.id
    )
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^unit (?P<level>\w+)"))
async def on_unit_level(c: Client, cq: CallbackQuery):
    lang = cq._lang
    level = cq.matches[0]["level"]
    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)
    price = strip_float(prices["unit"][level])
    if balance < price:
        return await cq.answer(
            lang.not_enough_balance(balance=balance, price=price), show_alert=True
        )
    available = await Card.filter(level=level.upper(), owner=None, dead=False)
    if level in ["elo"]:
        available = await Card.filter(vendor=level.upper(), owner=None, dead=False)
    if not len(available):
        return await cq.answer(
            lang.no_ccs_of_chosen_level(level=level.upper()), show_alert=True
        )

    keyb = ikb(
        [[(lang.confirm_buy, f"confirm_buy unit " + level)], [("<<", "buy_cc_unit")]]
    )
    text = lang.confirm_buy_text(
        product=cq.data.upper(),
        price=price,
        balance=balance,
        time_exchange=get_time_for_exchange(cq.data),
    )
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^buy_cc_mix$"))
async def on_buy_cc_mix(c: Client, cq: CallbackQuery):
    lang = cq._lang
    products = []
    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)
    for quant, price in prices["mix"].items():
        if int(quant) >= 200:
            break
        price = strip_float(price)
        products.append((f"{quant} Mix — R${price}", f"mix {quant}"))
    lines = array_chunk(products, 2)
    lines.append([(lang.to_resell, "mix_to_resell")])
    lines.append([("<<", "buy_cc")])
    keyb = ikb(lines)
    text = lang.buy_cc_mix_text + lang.wallet_info(
        balance=balance, user_id=cq.from_user.id
    )
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^mix_to_resell$"))
async def on_buy_mix_resell(c: Client, cq: CallbackQuery):
    lang = cq._lang
    products = []
    if cq.from_user.id in admins:
        for quant, price in prices["mix"].items():
            if int(quant) < 200:
                continue
            price = strip_float(price)
            products.append((f"{quant} Mix — R${price}", f"mix {quant}"))
        lines = array_chunk(products, 2)
    else:
        lines = []
    lines.append([("<<", "buy_cc_mix")])
    keyb = ikb(lines)
    text = (
        lang.buy_mix_resell if cq.from_user.id in admins else lang.buy_mix_resell_denied
    )
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^mix (?P<mix_quant>\d+)"))
async def on_buy_mix_confirm_ask(c: Client, cq: CallbackQuery):
    lang = cq._lang
    mix_quant = cq.matches[0]["mix_quant"]
    if int(mix_quant) >= 200 and cq.from_user.id not in admins:
        return await cq.answer(lang.buy_mix_resell_denied, show_alert=True)
    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)
    price = strip_float(prices["mix"][mix_quant])
    if balance < price:
        return await cq.answer(
            lang.not_enough_balance(balance=balance, price=price), show_alert=True
        )
    available = await Card.filter(owner=None)
    if int(mix_quant) < 50:
        available = [
            x
            for x in available
            if x.level.upper() not in ("BLACK", "BUSINESS", "INFINITE")
        ]
    if len(available) < int(mix_quant):
        return await cq.answer(
            lang.not_enough_available_ccs_for_mix_quant(available=len(available)),
            show_alert=True,
        )

    keyb = ikb(
        [
            [(lang.confirm_buy, f"confirm_buy mix " + mix_quant)],
            [("<<", "buy_cc_mix" if int(mix_quant) < 200 else "mix_to_resell")],
        ]
    )
    text = lang.confirm_buy_text(
        product=cq.data.upper(),
        price=price,
        balance=balance,
        time_exchange=get_time_for_exchange(cq.data),
    )
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^buy_promos$"))
async def on_buy_promos(c: Client, cq: CallbackQuery):
    lang = cq._lang
    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)
    keyb = ikb([[("Promoção Nubank", "promo1")], [("<<", "buy_cc")]])
    text = lang.buy_promo_text + lang.wallet_info(
        balance=balance, user_id=cq.from_user.id
    )
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^promo1$"))
async def on_buy_promo1(c: Client, cq: CallbackQuery):
    keyb = ikb(
        [
            [("🟠 Gold 516220 - R$10", "bin 516220 1")],
            [("🟠 Gold 523421 - R$10", "bin 523421 1")],
            [("🟠 Gold 550209 - R$10", "bin 550209 1")],
            [("<<", "buy_cc")],
        ]
    )
    text = """Promoção Nubank:\n\nCompre CCs usando bins Gold da Nubank e pague só 10 reais pela Gold."""
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^buy_bin_unit$"))
async def on_buy_bin_unit(c: Client, cq: CallbackQuery):
    lang = cq._lang
    chat = cq.message.chat
    keyb = ikb([[("<<", "buy_cc")]])

    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)

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
                lang.ask_bin_to_search, reply_markup=keyb, timeout=300
            )
        except listen.ListenerCanceled:
            return
        if not msg.text:
            await msg.reply(lang.expecting_text_msg, quote=True)
            continue
        card_bin = re.match(r"(\d{6})$", msg.text)
        if not card_bin:
            await msg.reply(lang.no_bin_found_to_search, quote=True)
            continue
        break
    if last_msg:
        await last_msg.request.remove_keyboard()

    # search for cards in db
    card_bin = int(card_bin[1])
    cards = await Card.filter(card_bin=card_bin, owner=None, dead=False)
    total = len(cards)

    if not total:
        text = lang.no_cards_found_by_bin(card_bin=card_bin)
    else:
        text = lang.cards_found_by_bin(
            total=total, card_bin=card_bin, level=cards[0].level
        ) + lang.wallet_info(balance=balance, user_id=cq.from_user.id)

        bin_info = await search_bin(card_bin)
        if not bin_info or not bin_info["level"]:
            return await msg.reply(lang.could_not_get_bin_info)
        if bin_info["level"].lower() not in prices["unit"]:
            return await msg.reply(lang.prices_has_not_level(level=bin_info["level"]))
        price = prices["specific"].get(
            str(card_bin), strip_float(prices["unit"][bin_info["level"].lower()])
        )

        keyb = ikb(
            [
                [
                    ("➖", "decrease_bin_quant"),
                    (lang.buy_bin(quant=1, price=1 * price), f"bin {card_bin} 1"),
                    ("➕", "increase_bin_quant"),
                ],
                [("<<", "buy_cc")],
            ]
        )
        if total == 1:
            keyb = ikb(
                [
                    [(lang.buy_bin(quant=1, price=1 * price), f"bin {card_bin} 1")],
                    [("<<", "buy_cc")],
                ]
            )

    await msg.reply(text, keyb, quote=True)


@Client.on_callback_query(filters.regex(r"(?P<action>in|de)crease_bin_quant"))
async def change_bin_quant(c: Client, cq: CallbackQuery):
    lang = cq._lang
    decrease = cq.matches[0]["action"] == "de"
    keyb = cq.message.ikb()
    cat, card_bin, quant = keyb[0][1][1].split(" ")
    quant = int(quant)
    if decrease:
        quant -= 1
    else:
        quant += 1

    cards = await Card.filter(card_bin=card_bin, owner=None, dead=False)
    if quant > len(cards):
        quant = 1
    elif quant < 1:
        quant = len(cards)

    bin_info = await search_bin(card_bin)
    if not bin_info or not bin_info["level"]:
        return await cq.answer(lang.could_not_get_bin_info, show_alert=True)
    if bin_info["level"].lower() not in prices["unit"]:
        return await cq.answer(
            lang.prices_has_not_level(level=bin_info["level"]), show_alert=True
        )
    price = prices["specific"].get(
        card_bin, strip_float(prices["unit"][bin_info["level"].lower()])
    )

    if len(cards) == 1:
        keyb = ikb(
            [
                [(lang.buy_bin(quant=1, price=1 * price), f"bin {card_bin} 1")],
                [("<<", "buy_cc")],
            ]
        )

    keyb[0][1][1] = f"{cat} {card_bin} {quant}"
    text = lang.buy_bin(quant=quant, price=quant * price)
    keyb[0][1][0] = text
    keyb = ikb(keyb)
    await cq.edit(cq.message.text.html, keyb)


@Client.on_callback_query(filters.regex(r"^bin (?P<card_bin>\d+) (?P<quant>\d+)"))
async def buy_bin(c: Client, cq: CallbackQuery):
    lang = cq._lang
    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)

    card_bin = cq.matches[0]["card_bin"]
    quant = int(cq.matches[0]["quant"])
    bin_info = await search_bin(card_bin)
    if not bin_info or not bin_info["level"]:
        return await cq.answer(lang.could_not_get_bin_info, show_alert=True)
    if bin_info["level"].lower() not in prices["unit"]:
        return await cq.answer(
            lang.prices_has_not_level(level=bin_info["level"]), show_alert=True
        )

    price = prices["specific"].get(
        card_bin, strip_float(prices["unit"][bin_info["level"].lower()])
    )
    price = quant * price
    if balance < price:
        return await cq.answer(
            lang.not_enough_balance(balance=balance, price=price), show_alert=True
        )

    cards = await Card.filter(card_bin=card_bin, owner=None, dead=False)
    if len(cards) < quant:
        return await cq.answer(lang.not_enough_ccs_for_bin(available=len(cards)))

    keyb = ikb([[(lang.confirm_buy, f"confirm_buy " + cq.data)], [("<<", "buy_cc")]])
    text = lang.confirm_buy_text(
        product=f"BIN {card_bin} x{quant}",
        price=price,
        balance=balance,
        time_exchange=get_time_for_exchange(cq.data),
    )
    await cq.edit(text, keyb)


@Client.on_callback_query(filters.regex(r"^confirm_buy (?P<item>.+)"))
async def confirm_buy(c: Client, cq: CallbackQuery):
    lang = cq._lang
    user_db = await User.get(id=cq.from_user.id)
    if user_db.last_bought:
        now = datetime.now(timezone.utc)
        delta = now - user_db.last_bought
        seconds_passed = delta.total_seconds()
        if seconds_passed < 30:
            return await cq.answer(lang.error_too_short_buy_interval, show_alert=True)
    await user_db.update(last_bought=datetime.now(timezone.utc))

    product = cq.matches[0]["item"]
    category, subcategory = product.split(" ", 1)
    if category != "bin" and (
        category not in prices or subcategory not in prices[category]
    ):
        return await cq.answer(lang.product_not_available_anymore, show_alert=True)
    if category != "bin":
        price = strip_float(prices[category][subcategory])
    else:
        card_bin, quant = subcategory.split(" ")
        quant = int(quant)
        first_card = (await Card.filter(card_bin=card_bin, owner=None, dead=False))[0]
        price = prices["specific"].get(
            card_bin, strip_float(prices["unit"][first_card.level.lower()])
        )
        price = quant * price

    balance = strip_float(user_db.balance)
    if balance < price:
        return await cq.answer(
            lang.not_enough_balance(balance=balance, price=price), show_alert=True
        )

    await cq.edit(lang.processing_order)

    if category == "unit":
        keyb = ikb([[("<<", "buy_cc_unit")]])
        level = subcategory
        available = await Card.filter(level=level.upper(), owner=None, dead=False)
        if level in ["elo"]:
            available = await Card.filter(vendor=level.upper(), owner=None, dead=False)

        if not len(available):
            return await cq.edit(lang.no_ccs_of_chosen_level(level=level.upper()), keyb)

        user_db = await User.get(id=cq.from_user.id)
        balance = strip_float(user_db.balance - price)
        await user_db.update(balance=balance)

        # choose a live card
        live = False
        while not live and len(available):
            card = random.choice(available)
            available.remove(card)
            live, card_repr, gate = True, None, None

            if live is True:
                 break
            elif live is False:
                await card.update(dead=True)
            elif live:
                print(f"API returned unknown result: {live}, {card_repr}")
            elif live is None:
                print("All Gates are off")
                break
            else:
                print(f"I don't know what live means: {live}")
        
        if not live:
            user_db = await User.get(id=cq.from_user.id)
            balance = strip_float(user_db.balance + price)
            await user_db.update(balance=balance)
            await cq.edit(lang.not_enough_ccs(price=price), keyb)
            return

        now = datetime.now(timezone.utc)
        await card.update(owner=cq.from_user.id, bought_date=now, plan=product.upper())
        date = card.date.replace("/", "|")
        cvv = str(card.cvv).zfill(3)
        #cpfs = await Cpfs.all().filter(owner=None)
        #rcpf = random.choice(cpfs)
        #await rcpf.update(owner=cq.from_user.id, linked_to_card=card.number)
        rcpf = await get_random_person()
        cpf_msg = f"\n\nCPF: {rcpf.get('cpf')}\nNome: {rcpf.get('nome')}"
        cards_str = (
            f"\nNÚMERO: {card.number}\nDATA: {date}\nCVV: {cvv}\nNÍVEL: {card.level}\nTIPO DE CARTÃO: {card.card_type}\nBANDEIRA: {card.vendor}\nBANCO: {card.bank}\nNACIONALIDADE: {card.country}"
        )
        admin_str = cards_str + f"|GATE_{gate}"

        text = lang.infocc_buy_succeeded(
            price=price,
            product=product.upper(),
            cards_str=cards_str,
            extra_data=cpf_msg,
            owner=cq.from_user.id,
            balance=balance,
            time_exchange=pretty_time_delta(get_time_for_exchange(product)),
        )
        print(text)
        await cq.edit(text)
        await cq.message.reply(lang.click_back, keyb)

    elif category == "mix":
        quant = int(subcategory)
        keyb = ikb([[("<<", "buy_cc_mix" if quant < 200 else "mix_to_resell")]])

        available = await Card.filter(owner=None, dead=False)
        if quant < 50:
            available = [
                x
                for x in available
                if x.level.upper() not in ("BLACK", "BUSINESS", "INFINITE", "PLATINUM")
            ]
        if len(available) < quant:
            return await cq.edit(
                lang.not_enough_available_ccs_for_mix_quant(available=len(available)),
                keyb,
            )

        user_db = await User.get(id=cq.from_user.id)
        balance = strip_float(user_db.balance - price)
        await user_db.update(balance=balance)

        if quant > 30:
            cards = random.sample(available, quant)
        else:
            cards = []
            while len(available) and len(cards) < quant:
                live = False
                while not live and len(available):
                    card = random.choice(available)
                    available.remove(card)
                    live, card_repr, gate = True, None, None
                    if live == True:
                        break
                    elif live == False:
                        await card.update(dead=True)
                    elif live:
                        print(f"API returned unknown result: {live}, {card_repr}")
                    elif live == None:
                        print("All Gates are off")
                        break
                    else:
                        print(f"I don't know what live means: {live}")
                card.gate = gate
                cards.append(card)

            if len(cards) < quant:
                user_db = await User.get(id=cq.from_user.id)
                balance = strip_float(user_db.balance + price)
                await user_db.update(balance=balance)
                await cq.edit(lang.not_enough_ccs(price=price), keyb)
                return

        cards_str = []
        admin_str = []
        now = datetime.now(timezone.utc)
        for card in cards:
            await card.update(
                owner=cq.from_user.id, bought_date=now, plan=product.upper()
            )
            date = card.date.replace("/", "|")
            cvv = str(card.cvv).zfill(3)
            if hasattr(card, "gate"):
                #cpfs = await Cpfs.all().filter(owner=None)
                #rcpf = random.choice(cpfs)
                #await rcpf.update(owner=cq.from_user.id, linked_to_card=card.number)
                rcpf = await get_random_person()
                cards_str.append(
                    f"\nNÚMERO: {card.number}\nDATA: {date}\nCVV: {cvv}\nNÍVEL: {card.level}\nTIPO DE CARTÃO: {card.card_type}\nBANDEIRA: {card.vendor}\nBANCO: {card.bank}\nNACIONALIDADE: {card.country}\n\nNome: {rcpf.get('nome')}\nCPF: {rcpf.get('cpf')}"
                )
            else:
                cards_str.append(
                    f"\nNÚMERO: {card.number}\nDATA: {date}\nCVV: {cvv}\nNÍVEL: {card.level}\nTIPO DE CARTÃO: {card.card_type}\nBANDEIRA: {card.vendor}\nBANCO: {card.bank}\nNACIONALIDADE: {card.country}"
                )
            if not hasattr(card, "gate"):
                card.gate = "00"
            admin_str.append(cards_str[-1] + f"\n\nGate: GATE_{card.gate}")
        cards_str = "\n".join(cards_str)
        admin_str = "\n".join(admin_str)

        text = lang.infocc_buy_succeeded(
            price=price,
            product=product.upper(),
            cards_str=cards_str,
            owner=cq.from_user.id,
            balance=balance,
            time_exchange=pretty_time_delta(get_time_for_exchange(product)),
        )
        if len(cards_str) > 1000:
            text = lang.infocc_buy_succeeded_file(
                price=price,
                product=product.upper(),
                owner=cq.from_user.id,
                balance=balance,
                time_exchange=pretty_time_delta(get_time_for_exchange(product)),
            )
            await cq.edit(text)
            filename = product.lower().replace(" ", "_") + str(cq.from_user.id) + ".txt"
            with open(filename, "w") as f:
                f.write(cards_str)
            await cq.message.reply_document(filename)
            os.remove(filename)
        else:
            await cq.edit(text)
        await cq.message.reply(lang.click_back, keyb)

    elif category == "bin":
        keyb = ikb([[("<<", "buy_cc")]])
        card_bin, quant = subcategory.split(" ")
        quant = int(quant)
        available = await Card.filter(card_bin=card_bin, owner=None, dead=False)

        user_db = await User.get(id=cq.from_user.id)
        balance = strip_float(user_db.balance - price)
        await user_db.update(balance=balance)

        cards = []
        live = True

        while not live and len(available) and len(cards) < quant:
            card = random.choice(available)
            available.remove(card)
            live, card_repr, gate = True, None, None
            if live is True:
                card.gate = gate
                cards.append(card)
            elif live is False:
                await card.update(dead=True)
            elif live:
                print(f"API returned unknown result: {live}, {card_repr}")
            elif live is None:
                print("All Gates are off")
                continue
            else:
                print(f"I don't know what live means: {live}")

        if len(cards) < quant:
            user_db = await User.get(id=cq.from_user.id)
            balance = strip_float(user_db.balance + price)
            await user_db.update(balance=balance)
            return await cq.edit(
                lang.not_enough_ccs_for_bin(available=len(cards)), keyb
            )

        cards_str = []
        admin_str = []
        now = datetime.now(timezone.utc)
        for card in cards:
            await card.update(
                owner=cq.from_user.id,
                bought_date=now,
                plan=f"BIN {card_bin} x{quant}",
            )
            date = card.date.replace("/", "|")
            cvv = str(card.cvv).zfill(3)
            #cpfs = await Cpfs.all().filter(owner=None)
            #rcpf = random.choice(cpfs)
            #await rcpf.update(owner=cq.from_user.id, linked_to_card=card.number)
            rcpf = await get_random_person()
            cards_str.append(
                f"\nNÚMERO: {card.number}\nDATA: {date}\nCVV: {cvv}\nNÍVEL: {card.level}\nTIPO DE CARTÃO: {card.card_type}\nBANDEIRA: {card.vendor}\nBANCO: {card.bank}\nNACIONALIDADE: {card.country}\n\nNome: {rcpf.get('nome')}\nCPF:{rcpf.get('cpf')}"
            )
            admin_str.append(cards_str[-1] + f"|GATE_{card.gate}")
        cards_str = "\n".join(cards_str)
        admin_str = "\n".join(admin_str)

        text = lang.infocc_buy_succeeded(
            price=price,
            product=f"BIN {card_bin} x{quant}",
            cards_str=cards_str,
            owner=cq.from_user.id,
            balance=balance,
            time_exchange=pretty_time_delta(get_time_for_exchange(product)),
        )
        await cq.edit(text)
        await cq.message.reply(lang.click_back, keyb)

    text = lang.buy_alert
    text.escape_html = False
    user = cq.from_user
    mention = (
        f"@{user.username}"
        if user.username
        else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    )
    text = text(
        mention=mention,
        user_id=user.id,
        price=price,
        balance=strip_float(balance),
        item=product.upper() if category != "bin" else f"BIN {card_bin} x{quant}",
        cards_str=admin_str if len(admin_str) < 1000 else "",
    )
    await c.send_message(admin_chat, text)
    if len(admin_str) >= 1000:
        filename = product.lower().replace(" ", "_") + str(cq.from_user.id) + ".txt"
        with open(filename, "w") as f:
            f.write(admin_str)
        await c.send_document(admin_chat, filename)
        os.remove(filename)
