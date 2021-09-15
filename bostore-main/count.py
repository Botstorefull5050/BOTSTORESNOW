import httpx
import sqlite3


db = sqlite3.connect("database.sqlite")

cur = db.cursor()


client = httpx.Client()


users = cur.execute("select id from user").fetchall()

data = []

for i, user in enumerate(users):
    print(i, len(users))
    count = cur.execute("select count(number) from card where owner = ?", user).fetchone()
    if count[0] > -1:
        r = client.post("https://api.telegram.org/1622670544:AAGbns04nmzcoviLbFwS-_rEhuZNRtc03AY/getChat", data=dict(chat_id=user[0]))
        rjson = r.json()
        if not rjson["ok"]:
            print(f"{user[0]} skipped: {rjson}")
            data.append(dict(id=user[0], name="#NOTFOUND", username="Desconhecido", count=count[0]))
            continue
        result = rjson["result"]
        data.append(dict(id=result.get("id"), name=result.get("first_name", "#DELETED").replace(",", r"\,"), username=result.get("username", "Nenhum"), count=count[0]))

data = sorted(data, key=lambda d: d["count"], reverse=True)

result = ""

for dado in data:
    result += f"{dado.get('count')},{dado.get('id')},{dado.get('username')},{dado.get('name')}\n"

with open("users.csv", "w") as f:
    f.write(result)
