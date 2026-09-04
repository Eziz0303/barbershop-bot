import logging
from typing import Optional

import httpx

from config import ADMIN_IDS, BOT_TOKEN
from models import Booking, Master, Service, Slot

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_telegram_message(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> None:
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)


CONFIRMED_TEMPLATES = {
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

REJECTED_TEMPLATES = {
    "ru": (
        "❌ К сожалению, запись отклонена.\n\n"
        "Мастер: {master}\n"
        "Услуга: {service}\n"
        "Дата: {date}\n"
        "Время: {time}\n\n"
        "Причина: {reason}\n\n"
        "Попробуйте выбрать другое время."
    ),
    "tk": (
        "❌ Gynansak-da, ýazgy ret edildi.\n\n"
        "Ussa: {master}\n"
        "Hyzmat: {service}\n"
        "Sene: {date}\n"
        "Wagt: {time}\n\n"
        "Sebäbi: {reason}\n\n"
        "Başga wagt saýlap görüň."
    ),
}

CANCELLED_ADMIN_TEXT = (
    "🚫 Клиент отменил запись\n\n"
    "Клиент: {client}\n"
    "Телефон: {phone}\n"
    "Мастер: {master}\n"
    "Услуга: {service}\n"
    "Дата: {date} {time}"
)

EXPIRE_REASON = {
    "ru": "Администратор не подтвердил запись в течение часа.",
    "tk": "Administrator bir sagadyň dowamynda ýazgyny tassyklamady.",
}


def _format_booking(master: Master, service: Service, slot: Slot, language: str = "ru") -> dict:
    master_name = master.name_tk if language == "tk" else master.name_ru
    service_name = service.name_tk if language == "tk" else service.name_ru
    return {
        "master": master_name,
        "service": service_name,
        "date": slot.slot_date.strftime("%d.%m.%Y"),
        "time": slot.slot_time.strftime("%H:%M"),
        "price": service.price,
    }


async def notify_admin_new_booking(booking: Booking, master: Master, service: Service, slot: Slot) -> None:
    fields = _format_booking(master, service, slot, "ru")
    admin_text = (
        "🆕 Новая запись — требует подтверждения\n\n"
        f"Клиент: {booking.client_name}\n"
        f"Телефон: {booking.client_phone}\n"
        f"Мастер: {fields['master']}\n"
        f"Услуга: {fields['service']}\n"
        f"Дата: {fields['date']} {fields['time']}\n"
        f"Стоимость: {fields['price']} TMT\n\n"
        "Подтвердите в течение часа, иначе клиенту автоматически придёт отказ."
    )
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Подтвердить", "callback_data": f"confirm:{booking.id}"},
                {"text": "❌ Отклонить", "callback_data": f"reject:{booking.id}"},
            ]
        ]
    }
    for admin_id in ADMIN_IDS:
        try:
            await send_telegram_message(admin_id, admin_text, reply_markup=reply_markup)
        except httpx.HTTPError:
            logger.warning(
                "Failed to notify admin chat_id=%s about new booking id=%s",
                admin_id,
                booking.id,
                exc_info=True,
            )


async def notify_client_confirmed(booking: Booking, master: Master, service: Service, slot: Slot) -> None:
    template = CONFIRMED_TEMPLATES.get(booking.language, CONFIRMED_TEMPLATES["ru"])
    text = template.format(**_format_booking(master, service, slot, booking.language))
    try:
        await send_telegram_message(booking.client_tg_id, text)
    except httpx.HTTPError:
        logger.warning(
            "Failed to notify client chat_id=%s about confirmed booking id=%s",
            booking.client_tg_id,
            booking.id,
            exc_info=True,
        )


async def notify_client_rejected(
    booking: Booking, master: Master, service: Service, slot: Slot, reason: str
) -> None:
    template = REJECTED_TEMPLATES.get(booking.language, REJECTED_TEMPLATES["ru"])
    text = template.format(reason=reason, **_format_booking(master, service, slot, booking.language))
    try:
        await send_telegram_message(booking.client_tg_id, text)
    except httpx.HTTPError:
        logger.warning(
            "Failed to notify client chat_id=%s about rejected booking id=%s",
            booking.client_tg_id,
            booking.id,
            exc_info=True,
        )


async def notify_admin_client_cancelled(booking: Booking, master: Master, service: Service, slot: Slot) -> None:
    fields = _format_booking(master, service, slot, "ru")
    text = CANCELLED_ADMIN_TEXT.format(
        client=booking.client_name,
        phone=booking.client_phone,
        master=fields["master"],
        service=fields["service"],
        date=fields["date"],
        time=fields["time"],
    )
    for admin_id in ADMIN_IDS:
        try:
            await send_telegram_message(admin_id, text)
        except httpx.HTTPError:
            logger.warning(
                "Failed to notify admin chat_id=%s about cancelled booking id=%s",
                admin_id,
                booking.id,
                exc_info=True,
            )
