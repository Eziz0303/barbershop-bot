import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from config import BOT_TOKEN, WEBAPP_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Записаться", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
    )
    await message.answer(
        "Добро пожаловать в Barbershop!\n"
        "Нажмите кнопку ниже или кнопку «Записаться» рядом с полем ввода, чтобы записаться.",
        reply_markup=keyboard,
    )


@dp.message()
async def fallback(message: Message) -> None:
    await message.answer(
        "Не понял команду. Нажмите «Записаться» рядом с полем ввода или отправьте /start."
    )


async def on_startup(bot: Bot) -> None:
    await bot.set_my_commands([BotCommand(command="start", description="Записаться в барбершоп")])
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Записаться", web_app=WebAppInfo(url=WEBAPP_URL))
    )
    logger.info("Menu button and commands configured, WEBAPP_URL=%s", WEBAPP_URL)


async def main() -> None:
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
