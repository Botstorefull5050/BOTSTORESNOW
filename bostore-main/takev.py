import sys
import sqlite3

db = sqlite3.connect("database.sqlite")

dbc = db.cursor()

dbc.execute("select number, date, cvv, level, card_type, vendor, added_date, owner from card where not owner is NULL")
all = dbc.fetchall()

for i in all:
    print("|".join([str(k) for k in i]))
    dbc.execute("delete from card where number = ?", (i[0],))

db.commit()
