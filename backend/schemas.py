import re
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator

PHONE_REGEX = re.compile(r"^\+993\d{8}$")


class MasterRead(BaseModel):
    id: int
    name_ru: str
    name_tk: str
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True


class ServiceRead(BaseModel):
    id: int
    name_ru: str
    name_tk: str
    duration_minutes: int
    price: int

    class Config:
        from_attributes = True


class MasterCreate(BaseModel):
    name_ru: str = Field(min_length=1, max_length=100)
    name_tk: str = Field(min_length=1, max_length=100)

    @field_validator("name_ru", "name_tk")
    @classmethod
    def validate_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым")
        return v


class ServiceCreate(BaseModel):
    name_ru: str = Field(min_length=1, max_length=100)
    name_tk: str = Field(min_length=1, max_length=100)
    duration_minutes: int = Field(gt=0, le=600)
    price: int = Field(gt=0)

    @field_validator("name_ru", "name_tk")
    @classmethod
    def validate_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название не может быть пустым")
        return v


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


class RejectBooking(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Причина не может быть пустой")
        return v


class CancelBooking(BaseModel):
    client_tg_id: int = Field(gt=0)


class MyBookingRead(BaseModel):
    id: int
    master_name: str
    service_name: str
    slot_date: date
    slot_time: time
    status: str
    price: int
