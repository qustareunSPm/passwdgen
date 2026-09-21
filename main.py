import asyncio
import html
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import BOT_TOKEN
from password_gen import PASSWORD_LENGTH, generate_password

dp = Dispatcher()

KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="🔄 Ещё один", callback_data="regen")]]
)


def format_password() -> str:
    pwd = html.escape(generate_password())
    return f"🔐 Ваш пароль ({PASSWORD_LENGTH} символов):\n\n<code>{pwd}</code>\n\nНажмите на пароль, чтобы скопировать."


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        f"Привет! Я генерирую надёжные {PASSWORD_LENGTH}-значные пароли.\n"
        "Отправьте /password или просто нажмите кнопку ниже."
    )
    await message.answer(format_password(), reply_markup=KEYBOARD)


@dp.message(Command("password"))
async def password(message: Message) -> None:
    await message.answer(format_password(), reply_markup=KEYBOARD)


@dp.callback_query(F.data == "regen")
async def regen(callback: CallbackQuery) -> None:
    await callback.message.edit_text(format_password(), reply_markup=KEYBOARD)
    await callback.answer()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
