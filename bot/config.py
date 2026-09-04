import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")
INTERNAL_API_TOKEN: str = os.getenv("INTERNAL_API_TOKEN", "")
BACKEND_INTERNAL_URL: str = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения (.env)")
if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL не задан в переменных окружения (.env)")
if not INTERNAL_API_TOKEN:
    raise RuntimeError("INTERNAL_API_TOKEN не задан в переменных окружения (.env)")
