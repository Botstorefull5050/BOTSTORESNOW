import random
import sys
import sqlite3

db = sqlite3.connect("database.sqlite")

dbc = db.cursor()

fname, level, quantity = sys.argv

level = level.upper()
quantity = int(quantity)

if level == "NULL":
    dbc.execute("select number, date, cvv, level, card_type, vendor from card where dead = ? and owner is ?", (False, None))
    all = dbc.fetchall()
else:
    dbc.execute("select number, date, cvv, level, card_type, vendor from card where dead = ? and owner is ? and level = ?", (False, None, level))
    all = dbc.fetchall()

random.shuffle(all)

if len(all) < quantity:
    print("Não há CCs disponíves na quantidade especificada.")
else:
    for i in range(quantity):
        print("|".join(all[i]))
        dbc.execute("update card set owner = 1001 where number = ?", (all[i][0],))
