import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]
INTERNAL_API_TOKEN: str = os.getenv("INTERNAL_API_TOKEN", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения (.env)")
if not INTERNAL_API_TOKEN:
    raise RuntimeError("INTERNAL_API_TOKEN не задан в переменных окружения (.env)")
