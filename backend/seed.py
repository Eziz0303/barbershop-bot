from datetime import date, time, timedelta

from sqlmodel import Session, col, select

from models import Master, Service, Slot

DEMO_MASTERS = [
    {"name": "Алексей", "photo_url": None},
    {"name": "Игорь", "photo_url": None},
]

DEMO_SERVICES = [
    {"name": "Стрижка", "duration_minutes": 40, "price": 1500},
    {"name": "Стрижка + борода", "duration_minutes": 60, "price": 2200},
    {"name": "Оформление бороды", "duration_minutes": 25, "price": 900},
]

SLOT_HOURS = [10, 11, 12, 14, 15, 16, 17, 18]
SLOT_DAYS_AHEAD = 14


def seed_demo_data(session: Session) -> None:
    if not session.exec(select(Master)).first():
        session.add_all(Master(**m) for m in DEMO_MASTERS)
    if not session.exec(select(Service)).first():
        session.add_all(Service(**s) for s in DEMO_SERVICES)
    session.commit()


def ensure_future_slots(session: Session, days_ahead: int = SLOT_DAYS_AHEAD) -> None:
    """Держит для каждого активного мастера расписание на days_ahead дней вперёд.

    Без этого расписание, засеянное один раз при первом запуске, закончилось бы
    через SLOT_DAYS_AHEAD дней и бронирование сломалось бы в проде.
    """
    masters = session.exec(select(Master).where(Master.is_active == True)).all()  # noqa: E712
    today = date.today()
    target_dates = [today + timedelta(days=i) for i in range(1, days_ahead + 1)]

    for master in masters:
        existing_dates = set(
            session.exec(
                select(Slot.slot_date).where(
                    Slot.master_id == master.id,
                    col(Slot.slot_date).in_(target_dates),
                )
            ).all()
        )
        missing_dates = [d for d in target_dates if d not in existing_dates]
        new_slots = [
            Slot(master_id=master.id, slot_date=d, slot_time=time(h, 0))
            for d in missing_dates
            for h in SLOT_HOURS
        ]
        if new_slots:
            session.add_all(new_slots)

    session.commit()
