import sys
import sqlite3

db = sqlite3.connect("database.sqlite")

dbc = db.cursor()

dbc.execute("select number, date, cvv, level, card_type, vendor, added_date from card where dead = ?", (True,))
all = dbc.fetchall()

for i in all:
    print("|".join(i))
    dbc.execute("delete from card where number = ?", (i[0],))

db.commit()
