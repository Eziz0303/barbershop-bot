import logging

import httpx

from config import ADMIN_IDS, BOT_TOKEN
from models import Booking, Master, Service, Slot

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_telegram_message(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text})


CLIENT_TEXT_TEMPLATES = {
    "ru": (
        "✅ Запись подтверждена!\n\n"
        "Мастер: {master}\n"
        "Услуга: {service}\n"
        "Дата: {date}\n"
        "Время: {time}\n"
        "Стоимость: {price} TMT\n\n"
        "Ждём вас в барбершопе!"
    ),
    "tk": (
        "✅ Ýazgy tassyklandy!\n\n"
        "Ussa: {master}\n"
        "Hyzmat: {service}\n"
        "Sene: {date}\n"
        "Wagt: {time}\n"
        "Bahasy: {price} TMT\n\n"
        "Sizi garaşýarys!"
    ),
}


async def notify_booking_created(booking: Booking, master: Master, service: Service, slot: Slot) -> None:
    date_str = slot.slot_date.strftime("%d.%m.%Y")
    time_str = slot.slot_time.strftime("%H:%M")

    template = CLIENT_TEXT_TEMPLATES.get(booking.language, CLIENT_TEXT_TEMPLATES["ru"])
    client_text = template.format(
        master=master.name, service=service.name, date=date_str, time=time_str, price=service.price
    )
    admin_text = (
        "🆕 Новая запись\n\n"
        f"Клиент: {booking.client_name}\n"
        f"Телефон: {booking.client_phone}\n"
        f"Мастер: {master.name}\n"
        f"Услуга: {service.name}\n"
        f"Дата: {date_str} {time_str}"
    )

    try:
        await send_telegram_message(booking.client_tg_id, client_text)
    except httpx.HTTPError:
        logger.warning(
            "Failed to notify client chat_id=%s about booking id=%s",
            booking.client_tg_id,
            booking.id,
            exc_info=True,
        )

    for admin_id in ADMIN_IDS:
        try:
            await send_telegram_message(admin_id, admin_text)
        except httpx.HTTPError:
            logger.warning(
                "Failed to notify admin chat_id=%s about booking id=%s",
                admin_id,
                booking.id,
                exc_info=True,
            )
