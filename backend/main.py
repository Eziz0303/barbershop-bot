import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from admin_routers import router as admin_router
from database import engine, init_db
from internal_routers import router as internal_router
from routers import router
from seed import ensure_future_slots, seed_demo_data
from sqlmodel import Session
from tasks import cleanup_old_data, expire_pending_bookings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

MAINTENANCE_INTERVAL_SECONDS = 300


async def maintenance_loop() -> None:
    while True:
        try:
            with Session(engine) as session:
                await expire_pending_bookings(session)
                cleanup_old_data(session)
        except Exception:
            logger.exception("Maintenance loop iteration failed")
        await asyncio.sleep(MAINTENANCE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_demo_data(session)
        ensure_future_slots(session)
    task = asyncio.create_task(maintenance_loop())
    logger.info("Startup complete: DB ready, demo data and future slots ensured")
    yield
    task.cancel()


app = FastAPI(title="Barbershop Booking API", lifespan=lifespan)


@app.middleware("http")
async def no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(router)
app.include_router(admin_router)
app.include_router(internal_router)

app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
