# Barbershop Booking Bot

Telegram Web App для записи в барбершоп: выбор мастера, услуги, даты и времени — прямо внутри Telegram, без сторонних сайтов и приложений.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57?logo=sqlite&logoColor=white)

## Что это

Клиент открывает бота в Telegram, нажимает кнопку "Записаться" и внутри мессенджера — без перехода на сайт — проходит весь путь записи: мастер → услуга → дата/время → контакты → подтверждение. Бронирование сразу попадает в базу, а клиент и администратор получают уведомление в чат.

Интерфейс двуязычный (русский / туркменский), номер телефона — в туркменском формате (`+993XXXXXXXX`).

## Архитектура

```
Telegram-клиент
      │
      ├── aiogram-бот (bot/) ── только /start и постоянная кнопка меню, открывающая Web App
      │
      └── Web App (webapp/) ── статический HTML/CSS/JS, открывается внутри Telegram
                │
                ▼
        FastAPI backend (backend/)
                │
                ├── проверка подписи initData (HMAC-SHA256)
                ├── SQLite (WAL, внешние ключи) — мастера, услуги, слоты, записи
                └── уведомления клиенту и админу через Telegram Bot API
```

Оба сервиса — независимые Docker-контейнеры, работают от непривилегированного пользователя, БД — в именованном Docker volume.

## Безопасность

Ключевое требование проекта — ни одна запись не попадает в БД без проверки, что запрос действительно пришёл из Telegram-клиента этого бота:

1. Telegram подписывает `initData` (данные о пользователе) собственным HMAC-SHA256, используя токен бота как секрет
2. Backend на каждый защищённый запрос пересчитывает подпись из `X-Telegram-Init-Data` заголовка тем же алгоритмом и сверяет её через `hmac.compare_digest` (защита от timing-атак)
3. Проверяется `auth_date`, чтобы отклонять устаревшие (перехваченные) данные
4. Все входящие данные валидируются Pydantic-схемами (формат телефона, длина имени, диапазоны id)
5. Двойное бронирование одного слота исключено на уровне БД (`unique` constraint + перехват `IntegrityError`)

Подробности реализации — в [backend/security.py](backend/security.py).

## Стек

- **Backend**: FastAPI, SQLModel (SQLAlchemy + Pydantic), SQLite
- **Bot**: Aiogram 3.x (polling)
- **Frontend**: Vanilla HTML/CSS/JS, Telegram Web App JS SDK
- **Инфраструктура**: Docker, Docker Compose, healthcheck, non-root контейнеры

## Запуск локально

Требуется Docker Desktop и туннель до `localhost:8000` с HTTPS (Telegram Web App не открывается по HTTP) — например [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/):

```bash
cloudflared tunnel --url http://localhost:8000
```

1. Скопируй `.env.example` в `.env`, впиши свой `BOT_TOKEN` (от [@BotFather](https://t.me/BotFather)), `WEBAPP_URL` (ссылка из туннеля) и `ADMIN_IDS` (твой Telegram id, узнать можно у [@userinfobot](https://t.me/userinfobot))
2. Запусти:
   ```bash
   docker compose up -d --build
   ```
3. Открой бота в Telegram и нажми "Записаться"

⚠️ Ссылка `cloudflared` временная и меняется при каждом перезапуске — для постоянной работы нужен собственный домен (см. раздел ниже).

## Структура проекта

```
backend/          FastAPI: API, проверка initData, БД, уведомления
  main.py         точка входа, healthcheck, статика webapp/
  security.py     проверка HMAC-подписи Telegram initData
  routers.py      /api/masters, /api/services, /api/slots, /api/booking
  models.py       таблицы SQLModel
  schemas.py      Pydantic-валидация входящих данных
  notify.py       уведомления клиенту/админу через Telegram Bot API
  seed.py         демо-данные + автогенерация расписания на 14 дней вперёд
bot/               Aiogram: /start, постоянная кнопка меню
webapp/            Web App: index.html / style.css / app.js
docker-compose.yml
```

## Продакшен-чеклист

Для локальной демонстрации проект полностью рабочий и протестирован. Для постоянной работы на сервере дополнительно нужно:

- [ ] Постоянный домен + HTTPS вместо временного `cloudflared`-туннеля
- [ ] Регулярный бэкап Docker volume с SQLite
- [ ] Ограничение размера логов Docker (`max-size`/`max-file`)
- [ ] Reverse-proxy перед портом 8000, если сервис публикуется напрямую в интернет
