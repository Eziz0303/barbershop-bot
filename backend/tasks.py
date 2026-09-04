import logging
from datetime import date, datetime, timedelta

from sqlmodel import Session, col, select

from models import Booking, Master, Service, Slot
from notify import EXPIRE_REASON, notify_client_rejected

logger = logging.getLogger(__name__)

PENDING_TIMEOUT = timedelta(hours=1)
DATA_RETENTION_DAYS = 365


async def expire_pending_bookings(session: Session) -> None:
    cutoff = datetime.utcnow() - PENDING_TIMEOUT
    expired = session.exec(
        select(Booking).where(Booking.status == "pending", Booking.created_at < cutoff)
    ).all()

    for booking in expired:
        slot = session.get(Slot, booking.slot_id)
        master = session.get(Master, booking.master_id)
        service = session.get(Service, booking.service_id)
        reason = EXPIRE_REASON.get(booking.language, EXPIRE_REASON["ru"])

        booking.status = "expired"
        booking.reject_reason = reason
        if slot:
            slot.is_booked = False
            session.add(slot)
        session.add(booking)
        session.commit()
        session.refresh(booking)

        if slot and master and service:
            await notify_client_rejected(booking, master, service, slot, reason)
        logger.info("Booking id=%s expired after 1h without admin confirmation", booking.id)


def cleanup_old_data(session: Session) -> None:
    cutoff = date.today() - timedelta(days=DATA_RETENTION_DAYS)
    old_slots = session.exec(select(Slot).where(Slot.slot_date < cutoff)).all()
    if not old_slots:
        return

    old_slot_ids = [s.id for s in old_slots]
    old_bookings = session.exec(select(Booking).where(col(Booking.slot_id).in_(old_slot_ids))).all()

    for booking in old_bookings:
        session.delete(booking)
    for slot in old_slots:
        session.delete(slot)
    session.commit()

    logger.info(
        "Data retention cleanup: removed %s slot(s) and %s booking(s) older than %s days",
        len(old_slots),
        len(old_bookings),
        DATA_RETENTION_DAYS,
    )
