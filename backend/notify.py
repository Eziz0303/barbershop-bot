import httpx

from config import ADMIN_IDS, BOT_TOKEN
from models import Booking, Master, Service, Slot

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_telegram_message(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text})


async def notify_booking_created(booking: Booking, master: Master, service: Service, slot: Slot) -> None:
    date_str = slot.slot_date.strftime("%d.%m.%Y")
    time_str = slot.slot_time.strftime("%H:%M")

    client_text = (
        "✅ Запись подтверждена!\n\n"
        f"Мастер: {master.name}\n"
        f"Услуга: {service.name}\n"
        f"Дата: {date_str}\n"
        f"Время: {time_str}\n"
        f"Стоимость: {service.price} ₽\n\n"
        "Ждём вас в барбершопе!"
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
        pass

    for admin_id in ADMIN_IDS:
        try:
            await send_telegram_message(admin_id, admin_text)
        except httpx.HTTPError:
            pass
