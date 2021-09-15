from pyrogram import Client, filters
from pyrogram.types import Message
from tortoise.functions import Count

from config import admins
from database import Card


@Client.on_message(filters.command("estoque") & filters.user(admins))
async def on_stock(c: Client, m: Message):
    # disponíveis
    available_text = ["• <b>DISPONÍVEL</b>\n"]
    res = (
        await Card.annotate(count=Count("id"))
        .filter(owner=None, dead=False)
        .group_by("level")
        .order_by("-count")
        .values("level", "count")
    )
    for d in res:
        if not d["level"]:
            d["level"] = "*INDEFINIDO*"
        available_text.append(f"<b>{d['level']}</b> - <code>{d['count']}</code>")

    sum_count = sum([x["count"] for x in res])
    available_text.append(f"\n<b>TOTAL</b>: <code>{sum_count}</code>")
    available_text = "\n".join(available_text)
    await m.reply(available_text)

    # vendidas
    res = await Card.filter(owner__not_isnull=True)
    count = {}
    sold_text = ["• <b>VENDIDAS</b>\n"]
    for d in res:
        if not d.level:
            d.level = "*INDEFINIDO*"
        if d.level not in count:
            count[d.level] = 0
        count[d.level] += 1

    count = dict(sorted(count.items(), key=lambda x: x[1], reverse=True))

    for level, c in count.items():
        sold_text.append(f"<b>{level}</b> - <code>{c}</code>")

    sum_count = sum(count.values())
    sold_text.append(f"\n<b>TOTAL</b>: <code>{sum_count}</code>")
    sold_text = "\n".join(sold_text)
    await m.reply(sold_text)

    # dies
    res = await Card.filter(dead=True)
    count = {}
    dies_text = [f"• <b>TROCAS (DIES)</b>\n"]
    for d in res:
        if not d.level:
            d.level = "*INDEFINIDO*"
        if d.level not in count:
            count[d.level] = 0
        count[d.level] += 1

    count = dict(sorted(count.items(), key=lambda x: x[1], reverse=True))

    for level, c in count.items():
        dies_text.append(f"<b>{level}</b> - <code>{c}</code>")

    sum_count = sum(count.values())
    dies_text.append(f"\n<b>TOTAL</b>: <code>{sum_count}</code>")
    dies_text = "\n".join(dies_text)
    await m.reply(dies_text)
