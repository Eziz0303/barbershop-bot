import re
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator

PHONE_REGEX = re.compile(r"^\+993\d{8}$")


class MasterRead(BaseModel):
    id: int
    name: str
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class ServiceRead(BaseModel):
    id: int
    name: str
    duration_minutes: int
    price: int

    class Config:
        from_attributes = True


class SlotRead(BaseModel):
    id: int
    master_id: int
    slot_date: date
    slot_time: time

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    master_id: int = Field(gt=0)
    service_id: int = Field(gt=0)
    slot_id: int = Field(gt=0)
    client_name: str = Field(min_length=2, max_length=100)
    client_phone: str
    language: str = Field(default="ru")

    @field_validator("client_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым")
        return v

    @field_validator("client_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_REGEX.match(v):
            raise ValueError("Неверный формат телефона, ожидается +993XXXXXXXX")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in ("ru", "tk"):
            raise ValueError("Unsupported language")
        return v


class BookingRead(BaseModel):
    id: int
    master_id: int
    service_id: int
    slot_id: int
    client_name: str
    client_phone: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
