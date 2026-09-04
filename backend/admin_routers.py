from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select

from database import get_session
from models import Booking, Master, Service, Slot
from notify import notify_client_confirmed, notify_client_rejected
from report import generate_daily_report_pdf
from schemas import MasterCreate, RejectBooking, ServiceCreate
from security import verify_internal_token
from seed import ensure_future_slots

router = APIRouter(prefix="/api/admin", dependencies=[Depends(verify_internal_token)])


@router.post("/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: int, session: Session = Depends(get_session)):
    booking = session.get(Booking, booking_id)
    if booking is None or booking.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or already processed")

    master = session.get(Master, booking.master_id)
    service = session.get(Service, booking.service_id)
    slot = session.get(Slot, booking.slot_id)

    booking.status = "confirmed"
    session.add(booking)
    session.commit()
    session.refresh(booking)

    if master and service and slot:
        await notify_client_confirmed(booking, master, service, slot)

    return {"ok": True}


@router.post("/bookings/{booking_id}/reject")
async def reject_booking(booking_id: int, payload: RejectBooking, session: Session = Depends(get_session)):
    booking = session.get(Booking, booking_id)
    if booking is None or booking.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or already processed")

    master = session.get(Master, booking.master_id)
    service = session.get(Service, booking.service_id)
    slot = session.get(Slot, booking.slot_id)

    booking.status = "rejected"
    booking.reject_reason = payload.reason
    if slot:
        slot.is_booked = False
        session.add(slot)
    session.add(booking)
    session.commit()
    session.refresh(booking)

    if master and service and slot:
        await notify_client_rejected(booking, master, service, slot, payload.reason)

    return {"ok": True}


@router.get("/report")
async def daily_report(
    report_date: date_type = Query(default_factory=date_type.today),
    session: Session = Depends(get_session),
):
    rows = session.exec(
        select(Booking, Slot, Master, Service)
        .join(Slot, Booking.slot_id == Slot.id)
        .join(Master, Booking.master_id == Master.id)
        .join(Service, Booking.service_id == Service.id)
        .where(Slot.slot_date == report_date)
        .order_by(Slot.slot_time)
    ).all()

    report_rows = [
        {
            "time": slot.slot_time.strftime("%H:%M"),
            "master": master.name_ru,
            "service": service.name_ru,
            "client": booking.client_name,
            "phone": booking.client_phone,
            "status": booking.status,
            "price": service.price,
        }
        for booking, slot, master, service in rows
    ]

    pdf_bytes = generate_daily_report_pdf(report_rows, report_date)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{report_date}.pdf"'},
    )


@router.post("/masters", status_code=status.HTTP_201_CREATED)
async def create_master(payload: MasterCreate, session: Session = Depends(get_session)):
    master = Master(name_ru=payload.name_ru, name_tk=payload.name_tk)
    session.add(master)
    session.commit()
    session.refresh(master)

    ensure_future_slots(session)

    return {"id": master.id, "name_ru": master.name_ru, "name_tk": master.name_tk}


@router.post("/services", status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceCreate, session: Session = Depends(get_session)):
    service = Service(
        name_ru=payload.name_ru,
        name_tk=payload.name_tk,
        duration_minutes=payload.duration_minutes,
        price=payload.price,
    )
    session.add(service)
    session.commit()
    session.refresh(service)

    return {"id": service.id, "name_ru": service.name_ru, "name_tk": service.name_tk}
