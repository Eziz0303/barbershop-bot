from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, col, select

from database import get_session
from models import Booking, Master, Service, Slot
from notify import notify_admin_client_cancelled
from schemas import CancelBooking, MyBookingRead
from security import verify_internal_token

router = APIRouter(prefix="/api/internal", dependencies=[Depends(verify_internal_token)])

ACTIVE_STATUSES = ("pending", "confirmed")


@router.get("/bookings/my", response_model=list[MyBookingRead])
async def my_bookings(client_tg_id: int = Query(gt=0), session: Session = Depends(get_session)):
    rows = session.exec(
        select(Booking, Slot, Master, Service)
        .join(Slot, Booking.slot_id == Slot.id)
        .join(Master, Booking.master_id == Master.id)
        .join(Service, Booking.service_id == Service.id)
        .where(
            Booking.client_tg_id == client_tg_id,
            col(Booking.status).in_(ACTIVE_STATUSES),
            Slot.slot_date >= date.today(),
        )
        .order_by(Slot.slot_date, Slot.slot_time)
    ).all()

    return [
        MyBookingRead(
            id=booking.id,
            master_name=master.name_tk if booking.language == "tk" else master.name_ru,
            service_name=service.name_tk if booking.language == "tk" else service.name_ru,
            slot_date=slot.slot_date,
            slot_time=slot.slot_time,
            status=booking.status,
            price=service.price,
        )
        for booking, slot, master, service in rows
    ]


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: int, payload: CancelBooking, session: Session = Depends(get_session)):
    booking = session.get(Booking, booking_id)
    if booking is None or booking.client_tg_id != payload.client_tg_id or booking.status not in ACTIVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    master = session.get(Master, booking.master_id)
    service = session.get(Service, booking.service_id)
    slot = session.get(Slot, booking.slot_id)

    booking.status = "cancelled"
    if slot:
        slot.is_booked = False
        session.add(slot)
    session.add(booking)
    session.commit()
    session.refresh(booking)

    if master and service and slot:
        await notify_admin_client_cancelled(booking, master, service, slot)

    return {"ok": True}
