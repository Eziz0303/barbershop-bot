import asyncio
import logging
from datetime import date
from typing import Optional

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonWebApp,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from config import ADMIN_IDS, BACKEND_INTERNAL_URL, BOT_TOKEN, INTERNAL_API_TOKEN, WEBAPP_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# admin_id -> booking_id, ждём от админа текст с причиной отказа
pending_rejections: dict[int, int] = {}

STATUS_LABELS = {"pending": "⏳ ожидает подтверждения", "confirmed": "✅ подтверждена"}

BTN_BOOK = "📅 Записаться"
BTN_MY_BOOKINGS = "📋 Мои записи"
BTN_REPORT = "📊 Отчёт за сегодня"


def build_main_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=BTN_BOOK, web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text=BTN_MY_BOOKINGS)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=BTN_REPORT)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def backend_request(method: str, path: str, **kwargs) -> Optional[httpx.Response]:
    headers = {"X-Internal-Token": INTERNAL_API_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            return await client.request(method, f"{BACKEND_INTERNAL_URL}{path}", headers=headers, **kwargs)
    except httpx.HTTPError:
        logger.exception("Backend request failed: %s %s", method, path)
        return None


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        "Добро пожаловать в Barbershop!\nВыберите действие на клавиатуре ниже.",
        reply_markup=build_main_keyboard(is_admin),
    )


async def send_my_bookings(message: Message) -> None:
    resp = await backend_request(
        "GET", "/api/internal/bookings/my", params={"client_tg_id": message.from_user.id}
    )
    if resp is None or resp.status_code != 200:
        await message.answer("Не удалось получить список записей. Попробуйте позже.")
        return

    bookings = resp.json()
    if not bookings:
        await message.answer("У вас нет активных записей.")
        return

    for b in bookings:
        text = (
            f"{b['master_name']} — {b['service_name']}\n"
            f"{b['slot_date']} {b['slot_time'][:5]}\n"
            f"Статус: {STATUS_LABELS.get(b['status'], b['status'])}\n"
            f"Цена: {b['price']} TMT"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel:{b['id']}")]]
        )
        await message.answer(text, reply_markup=keyboard)


async def send_report(message: Message, report_date: str) -> None:
    resp = await backend_request("GET", "/api/admin/report", params={"report_date": report_date})
    if resp is None or resp.status_code != 200:
        await message.answer("Не удалось сформировать отчёт. Проверьте формат даты (ГГГГ-ММ-ДД).")
        return

    document = BufferedInputFile(resp.content, filename=f"report_{report_date}.pdf")
    await message.answer_document(document, caption=f"Отчёт за {report_date}")


@dp.message(Command("my"))
async def cmd_my(message: Message) -> None:
    await send_my_bookings(message)


@dp.message(F.text == BTN_MY_BOOKINGS)
async def kb_my_bookings(message: Message) -> None:
    await send_my_bookings(message)


@dp.message(Command("report"))
async def cmd_report(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = (message.text or "").split(maxsplit=1)
    report_date = parts[1].strip() if len(parts) > 1 else date.today().isoformat()
    await send_report(message, report_date)


@dp.message(F.text == BTN_REPORT)
async def kb_report(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    await send_report(message, date.today().isoformat())


@dp.callback_query(F.data.startswith("confirm:"))
async def on_confirm(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    booking_id = callback.data.split(":", 1)[1]
    resp = await backend_request("POST", f"/api/admin/bookings/{booking_id}/confirm")
    if resp is not None and resp.status_code == 200:
        await callback.message.edit_text(f"{callback.message.text}\n\n✅ Подтверждено", reply_markup=None)
        await callback.answer("Подтверждено")
    else:
        await callback.answer("Не удалось подтвердить (возможно, уже обработано)", show_alert=True)


@dp.callback_query(F.data.startswith("reject:"))
async def on_reject(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    booking_id = int(callback.data.split(":", 1)[1])
    pending_rejections[callback.from_user.id] = booking_id
    await callback.answer()
    await callback.message.answer("Напишите причину отказа одним сообщением:")


@dp.callback_query(F.data.startswith("cancel:"))
async def on_cancel(callback: CallbackQuery) -> None:
    booking_id = callback.data.split(":", 1)[1]
    resp = await backend_request(
        "POST",
        f"/api/internal/bookings/{booking_id}/cancel",
        json={"client_tg_id": callback.from_user.id},
    )
    if resp is not None and resp.status_code == 200:
        await callback.message.edit_text(f"{callback.message.text}\n\n❌ Отменено", reply_markup=None)
        await callback.answer("Запись отменена")
    else:
        await callback.answer("Не удалось отменить запись", show_alert=True)


@dp.message()
async def handle_text(message: Message) -> None:
    user_id = message.from_user.id

    if user_id in ADMIN_IDS and user_id in pending_rejections:
        booking_id = pending_rejections.pop(user_id)
        reason = (message.text or "").strip() or "Без указания причины"
        resp = await backend_request(
            "POST", f"/api/admin/bookings/{booking_id}/reject", json={"reason": reason}
        )
        if resp is not None and resp.status_code == 200:
            await message.answer(f"❌ Запись #{booking_id} отклонена, клиенту отправлено уведомление.")
        else:
            await message.answer("Не удалось отклонить запись (возможно, уже обработана).")
        return

    await message.answer(
        "Не понял команду. Пожалуйста, используйте кнопки меню ниже.",
        reply_markup=build_main_keyboard(user_id in ADMIN_IDS),
    )


async def on_startup(bot: Bot) -> None:
    default_commands = [
        BotCommand(command="start", description="Открыть меню"),
        BotCommand(command="my", description="Мои записи"),
    ]
    await bot.set_my_commands(default_commands)

    admin_commands = default_commands + [BotCommand(command="report", description="Отчёт за день (PDF)")]
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except TelegramAPIError:
            logger.warning("Could not set admin commands for chat_id=%s", admin_id)

    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Записаться", web_app=WebAppInfo(url=WEBAPP_URL))
    )
    logger.info("Bot commands and menu button configured, WEBAPP_URL=%s", WEBAPP_URL)


async def main() -> None:
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
