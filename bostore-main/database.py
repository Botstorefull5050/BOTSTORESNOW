import os

from tortoise import Tortoise
from tortoise import fields
from tortoise.models import Model


class Base(Model):
    class Meta:
        abstract = True

    async def update(self, **kwargs):
        return await self.get(pk=self.pk).update(**kwargs)


class User(Base):
    key = fields.IntField(pk=True)
    id = fields.IntField()
    balance = fields.FloatField(null=False, default=0.0)
    start_date = fields.DatetimeField(auto_now_add=True)
    waiting_for = fields.CharField(max_length=255, null=True)
    waiting_param = fields.JSONField(default="{}", null=True)
    waiting_cancelable = fields.CharField(max_length=255, null=True)
    language = fields.CharField(max_length=255, default="en")
    timezone = fields.CharField(max_length=255, default="UTC")
    agreed_tos = fields.BooleanField(default=False)
    last_bought = fields.DatetimeField(null=True)

    async def wait_for(self, waiting_for, waiting_param=None, cancelable=True):
        return await self.get(key=self.key).update(
            waiting_for=waiting_for,
            waiting_param=waiting_param,
            waiting_cancelable=cancelable,
        )

    async def wait_end(self):
        return await self.get(key=self.key).update(
            waiting_for=None, waiting_param=None, waiting_cancelable=None
        )


class Session(Base):
    id = fields.IntField(pk=True)
    key = fields.CharField(max_length=255)
    value = fields.CharField(max_length=255)


class Card(Base):
    id = fields.IntField(pk=True)
    added_date = fields.DatetimeField(auto_now_add=True)
    number = fields.CharField(max_length=255)
    date = fields.CharField(max_length=255)
    cvv = fields.CharField(max_length=255)
    country = fields.CharField(max_length=255)
    vendor = fields.CharField(max_length=255)
    card_type = fields.CharField(max_length=255)
    level = fields.CharField(max_length=255)
    bank = fields.CharField(max_length=255)
    card_bin = fields.CharField(max_length=255)
    bought_date = fields.DatetimeField(null=True)
    owner = fields.IntField(null=True, default=None)
    dead = fields.BooleanField(default=False)
    plan = fields.CharField(max_length=255, null=True)


class Cpfs(Base):
    added_date = fields.DatetimeField(auto_now_add=True)
    number = fields.CharField(max_length=255)
    owner = fields.IntField(null=True, default=None)
    linked_to_card = fields.CharField(null=True, max_length=255)


class Gift(Base):
    id = fields.IntField(pk=True)
    price = fields.FloatField()
    code = fields.CharField(max_length=255)


async def connect_database():
    await Tortoise.init(
        {
            "timezone": "UTC",
            "connections": {"bot_db": os.getenv("DATABASE_URL")},
            "apps": {"bot": {"models": [__name__], "default_connection": "bot_db"}},
        }
    )
    # Generate the schema
    await Tortoise.generate_schemas()
