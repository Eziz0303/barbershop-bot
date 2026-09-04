from datetime import date, datetime, time
from typing import Optional

from sqlmodel import Field, SQLModel


class Master(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    photo_url: Optional[str] = None
    is_active: bool = Field(default=True)


class Service(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    duration_minutes: int
    price: int
    is_active: bool = Field(default=True)


class Slot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: int = Field(foreign_key="master.id")
    slot_date: date
    slot_time: time
    is_booked: bool = Field(default=False)


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: int = Field(foreign_key="master.id")
    service_id: int = Field(foreign_key="service.id")
    slot_id: int = Field(foreign_key="slot.id", unique=True)
    client_tg_id: int
    client_name: str
    client_phone: str
    language: str = Field(default="ru")
    status: str = Field(default="confirmed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
