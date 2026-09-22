import asyncio
import contextlib
import html
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import storage
import vault
from config import ALLOWED_USER_ID, BOT_TOKEN
from password_gen import generate_password

log = logging.getLogger(__name__)

DELETE_AFTER = 60  # через сколько секунд удалить сообщение с паролем

dp = Dispatcher()
# Бот отвечает только владельцу
dp.message.filter(F.from_user.id == ALLOWED_USER_ID)


class Setup(StatesGroup):
    server = State()
    client_id = State()
    client_secret = State()
    password = State()


class NewPassword(StatesGroup):
    waiting_name = State()


async def delete_quietly(message: Message) -> None:
    with contextlib.suppress(Exception):
        await message.delete()


async def begin_setup(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Setup.server)
    await message.answer(
        "🔧 Настройка Vaultwarden (делается один раз).\n"
        "Сообщения с ключами я сразу удаляю из чата.\n\n"
        "1/4. Адрес сервера, например https://vault.example.com\n\n"
        "/cancel — отмена"
    )


# ---------- команды ----------

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    if storage.load() is None:
        await begin_setup(message, state)
        return
    await message.answer(
        "Привет! Команды:\n"
        "/new — создать пароль и сохранить в Vaultwarden\n"
        "/gen — просто сгенерировать пароль\n"
        "/setup — заново ввести данные Vaultwarden\n"
        "/cancel — отменить"
    )


@dp.message(Command("setup"))
async def setup(message: Message, state: FSMContext) -> None:
    await begin_setup(message, state)


@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.")


@dp.message(Command("gen"))
async def gen(message: Message) -> None:
    await message.answer(f"<code>{html.escape(generate_password())}</code>")


@dp.message(Command("new"))
async def new(message: Message, state: FSMContext) -> None:
    if storage.load() is None:
        await begin_setup(message, state)
        return
    await state.set_state(NewPassword.waiting_name)
    await message.answer("Для какого сервиса создать пароль?")


# ---------- первичная настройка ----------

@dp.message(Setup.server, F.text)
async def setup_server(message: Message, state: FSMContext) -> None:
    server = message.text.strip().rstrip("/")
    if not server.startswith(("http://", "https://")):
        server = "https://" + server
    await state.update_data(server=server)
    await state.set_state(Setup.client_id)
    await message.answer(
        "2/4. client_id.\n"
        "Веб-версия → Account settings → Security → Keys → View API key.\n"
        "Выглядит как user.xxxxxxxx-xxxx-…"
    )


@dp.message(Setup.client_id, F.text)
async def setup_client_id(message: Message, state: FSMContext) -> None:
    await delete_quietly(message)
    await state.update_data(client_id=message.text.strip())
    await state.set_state(Setup.client_secret)
    await message.answer("3/4. client_secret (оттуда же).")


@dp.message(Setup.client_secret, F.text)
async def setup_client_secret(message: Message, state: FSMContext) -> None:
    await delete_quietly(message)
    await state.update_data(client_secret=message.text.strip())
    await state.set_state(Setup.password)
    await message.answer("4/4. Мастер-пароль от Vaultwarden.")


@dp.message(Setup.password, F.text)
async def setup_password(message: Message, state: FSMContext) -> None:
    await delete_quietly(message)
    creds = {**await state.get_data(), "password": message.text}
    await state.clear()

    status = await message.answer("⏳ Проверяю подключение…")
    try:
        await vault.verify(creds)
    except Exception as e:
        log.exception("Проверка Vaultwarden не прошла")
        await status.edit_text(
            f"❌ Не удалось подключиться:\n<code>{html.escape(str(e)[:300])}</code>\n\n"
            "Попробовать снова: /setup"
        )
        return

    storage.save(creds)
    await status.edit_text("✅ Vaultwarden подключён. Теперь можно /new")


# ---------- создание пароля ----------

@dp.message(NewPassword.waiting_name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()[:100]
    await state.clear()

    creds = storage.load()
    if creds is None:
        await message.answer("Vaultwarden не настроен: /setup")
        return

    password = generate_password()
    status = await message.answer("⏳ Сохраняю в Vaultwarden…")

    try:
        await vault.add_login(creds, name, password)
    except Exception:
        log.exception("Не удалось сохранить в Vaultwarden")
        await status.edit_text("❌ Не удалось сохранить в Vaultwarden. Подробности в логах.")
        return

    await status.edit_text(
        f"✅ Сохранено в Vaultwarden: <b>{html.escape(name)}</b>\n\n"
        f"<code>{html.escape(password)}</code>\n\n"
        f"Сообщение удалится через {DELETE_AFTER} сек."
    )
    await asyncio.sleep(DELETE_AFTER)
    await delete_quietly(status)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
