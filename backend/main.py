from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from database import engine, init_db
from routers import router
from seed import seed_demo_data
from sqlmodel import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_demo_data(session)
    yield


app = FastAPI(title="Barbershop Booking API", lifespan=lifespan)


@app.middleware("http")
async def no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(router)

app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
