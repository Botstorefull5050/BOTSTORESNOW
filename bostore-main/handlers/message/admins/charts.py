import sqlite3
from datetime import datetime
from io import BytesIO

import matplotlib.pyplot as plt
from pyrogram import Client, filters

from config import admins

db = sqlite3.connect("database.sqlite")


def transform_data(values):
    data = {}

    for value in values:
        date = value[0].split(" ")[0]
        if data.get(date):
            data[date] += 1
        else:
            data[date] = 1

    x = [datetime.fromisoformat(x) for x in data.keys()]

    y = data.values()

    return x, y


@Client.on_callback_query(filters.regex(r"stats") & filters.user(admins))
async def stats(c, m):
    # TODO: Switch to tortoise ORM
    values = db.execute(
        "select bought_date from card where bought_date is not null and dead = 0 and plan not like 'TROCA%' order by bought_date asc"
    ).fetchall()

    valuesd = db.execute(
        "select bought_date from card where bought_date is not null and dead = 1 order by bought_date asc"
    ).fetchall()

    x, y = transform_data(values)
    x2, y2 = transform_data(valuesd)

    plt.title("Número de vendas e trocas")

    plt.plot(x, y, label="Vendas")
    plt.plot(x2, y2, label="Trocas")
    plt.grid()
    plt.legend()
    fig = plt.gcf()

    fig.set_size_inches(12.80, 7.20)
    bio = BytesIO()
    bio.name = "chart.png"
    plt.savefig(bio)
    plt.close()
    await m.message.reply_photo(bio)
