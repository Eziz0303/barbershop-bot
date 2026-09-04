from datetime import date as date_type
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database import get_session
from models import Booking, Master, Service, Slot
from notify import notify_booking_created
from schemas import BookingCreate, BookingRead, MasterRead, ServiceRead, SlotRead
from security import get_verified_telegram_user

router = APIRouter(prefix="/api", dependencies=[Depends(get_verified_telegram_user)])


@router.get("/masters", response_model=list[MasterRead])
def list_masters(session: Session = Depends(get_session)):
    return session.exec(select(Master).where(Master.is_active == True)).all()  # noqa: E712


@router.get("/services", response_model=list[ServiceRead])
def list_services(session: Session = Depends(get_session)):
    return session.exec(select(Service).where(Service.is_active == True)).all()  # noqa: E712


@router.get("/slots", response_model=list[SlotRead])
def list_slots(
    master_id: int,
    slot_date: date_type,
    session: Session = Depends(get_session),
):
    return session.exec(
        select(Slot).where(
            Slot.master_id == master_id,
            Slot.slot_date == slot_date,
            Slot.is_booked == False,  # noqa: E712
        )
    ).all()


@router.post("/booking", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    telegram_user: dict = Depends(get_verified_telegram_user),
    session: Session = Depends(get_session),
):
    slot = session.get(Slot, payload.slot_id)
    if slot is None or slot.master_id != payload.master_id or slot.is_booked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot unavailable")
    if datetime.combine(slot.slot_date, slot.slot_time) < datetime.now():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot unavailable")

    service = session.get(Service, payload.service_id)
    if service is None or not service.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    booking = Booking(
        master_id=payload.master_id,
        service_id=payload.service_id,
        slot_id=payload.slot_id,
        client_tg_id=telegram_user["id"],
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        language=payload.language,
    )
    slot.is_booked = True

    session.add(slot)
    session.add(booking)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot unavailable")

    session.refresh(booking)

    await notify_booking_created(booking, session.get(Master, booking.master_id), service, slot)

    return booking
