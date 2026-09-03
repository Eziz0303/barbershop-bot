from datetime import date, time, timedelta

from sqlmodel import Session, select

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
SLOT_DAYS_AHEAD = 7


def seed_demo_data(session: Session) -> None:
    if session.exec(select(Master)).first():
        return

    masters = [Master(**m) for m in DEMO_MASTERS]
    services = [Service(**s) for s in DEMO_SERVICES]
    session.add_all(masters)
    session.add_all(services)
    session.commit()

    today = date.today()
    slots = []
    for master in masters:
        for day_offset in range(1, SLOT_DAYS_AHEAD + 1):
            slot_date = today + timedelta(days=day_offset)
            for hour in SLOT_HOURS:
                slots.append(
                    Slot(master_id=master.id, slot_date=slot_date, slot_time=time(hour, 0))
                )
    session.add_all(slots)
    session.commit()
