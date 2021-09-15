import time
from typing import List

from pyrogram import Client, filters
from pyrogram.types import Message

from config import admins

from database import User


@Client.on_message(filters.command(["broadcast", "enviar"]) & filters.user(admins))
async def broadcast(c: Client, m: Message):
    await m.reply_text(
        "📣 Você está no <b>modo broadcast</b>, no qual você pode enviar mensagens para todos os usuários do bot. Por favor, envie a(s) mensagem(s) que você deseja enviar abaixo. <b>Envie /send para enviar a mensagem ou /cancel para cancelar.</b>"
    )
    last_msg = 0
    messages: List[Message] = []
    while True:
        msg = await c.listen(m.chat.id, timeout=300)
        if msg.text:
            if msg.text.startswith("/send"):
                break
            if msg.text.startswith("/cancel"):
                messages.clear()
                break
            messages.append(msg)
            await m.reply_text("✔️ Mensagem adicionada.")

    if not messages:
        await m.reply_text("❕ Não há nada para enviar. Comando cancelado.")
    else:
        sent = await m.reply_text("📣 Enviando mensagens...")
        all_users = await User.all().values("id")
        users_count = len(all_users)
        count = 0
        for i, u in enumerate(all_users):
            for message in messages:
                try:
                    await message.copy(u["id"])
                except:
                    pass
                else:
                    count += 1
            if time.time() - last_msg > 3:
                last_msg = time.time()
                try:
                    await sent.edit_text(
                        "📣 Enviando mensagens... {}% concluído.".format(
                            round((i / users_count) * 100, 2)
                        )
                    )
                except:
                    pass

        await sent.edit_text(f"✅ {count} mensagens foram enviadas.")
