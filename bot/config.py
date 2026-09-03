import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения (.env)")
if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL не задан в переменных окружения (.env)")
