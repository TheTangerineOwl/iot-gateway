"""
IoT Gateway Web UI — FastAPI приложение.

Точка входа:
    uvicorn web.backend.main:app --host 0.0.0.0 --port 8090

Маршруты:
    /web/api/auth/*     — авторизация (JWT)
    /web/api/gateway/*  — статус и конфигурация шлюза
    /web/api/devices/*  — управление устройствами
    /web/api/logs/*     — просмотр и стриминг логов
    /docs               — Swagger UI
    /redoc              — ReDoc
    /*                  — SPA (frontend static files, после сборки)
"""
import logging
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from web.backend.dependencies.database import close_db, init_db
from web.backend.dependencies.config import get_settings
from web.backend.routers import auth, devices, gateway, logs


BASE_DIR = Path(__file__).parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ENV_FILE = BASE_DIR.parent / '.env'
loaded_env = load_dotenv(ENV_FILE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager для FastAPI.

    Выполняет инициализацию БД при старте и закрытие при завершении.
    """
    settings = get_settings()
    if loaded_env:
        logger.info(f"Переменные окружения загружены из {ENV_FILE}")
    logger.info("Инициализация БД...")
    await init_db(settings)
    logger.info("БД инициализирована")

    logger.info("IoT Gateway Web UI запущен")
    if _static_dir.exists():
        logger.info("Статика фронтенда найдена: %s", _static_dir)
    else:
        logger.warning(
            "Директория статики не найдена: %s. "
            "Запустите сборку фронтенда (`npm run build` в web/frontend/).",
            _static_dir,
        )
    _assets_dir = _static_dir / "assets"
    if _assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(_assets_dir)),
            name="assets"
        )

    yield

    logger.info("Закрытие БД...")
    await close_db()
    logger.info("БД закрыта")


app = FastAPI(
    title="IoT Gateway Web UI",
    description=(
        "Веб-интерфейс для управления IoT Gateway.\n\n"
        "Все защищённые эндпоинты требуют JWT-токен:\n"
        "`Authorization: Bearer <token>`\n\n"
        "Получить токен: `POST /web/api/auth/login`"
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

_cors_origins_env = os.getenv("WEB__CORS_ORIGINS", "*")
_cors_origins = (
    ["*"]
    if _cors_origins_env == "*"
    else [o.strip() for o in _cors_origins_env.split(",")]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins_env != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/web/api/auth")
app.include_router(gateway.router, prefix="/web/api/gateway")
app.include_router(devices.router, prefix="/web/api/devices")
app.include_router(logs.router, prefix="/web/api/logs")

_static_dir = BASE_DIR / "static"


@app.get(
    "/{full_path:path}",
    response_model=None,
    include_in_schema=False,
    summary="SPA fallback — отдаёт index.html для фронтенд-роутинга",
)
async def spa_fallback(full_path: str) -> FileResponse | JSONResponse:
    """
    Фолбек для маршрутизации.

    Перехватывает все пути, не совпавшие с API или статикой,
    и возвращает index.html — необходимо для React Router.
    """
    index_html = _static_dir / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))

    return JSONResponse(
        status_code=503,
        content={
            "detail": "Frontend ещё не собран. "
            "Запустите `npm run build` в web/frontend/.",
            "docs": "/docs",
        },
    )
