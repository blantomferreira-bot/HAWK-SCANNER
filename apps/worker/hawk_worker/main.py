from hawk_worker.bootstrap import add_api_to_path

add_api_to_path()

from fastapi import FastAPI, Header, HTTPException, status  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.infrastructure.cache import cache  # noqa: E402
from src.infrastructure.database import SessionLocal  # noqa: E402

from hawk_worker.config import ScannerSettings
from hawk_worker.scanner import ScannerService
from hawk_worker.ml.service import DailyLearningService

settings = ScannerSettings.from_environment()
scanner = ScannerService(settings)
learning_service = DailyLearningService(settings)
app = FastAPI(title="HAWK SCANNER Worker", version="1.0.0", docs_url="/docs")


@app.get("/health")
@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "hawk-scanner-worker"}


@app.get("/health/ready")
async def health_ready() -> dict[str, str]:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        await (await cache.client()).ping()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stateful dependencies are unavailable",
        ) from error
    return {"status": "ready", "service": "hawk-scanner-worker"}


@app.post("/internal/scanner/run")
async def run_scanner(x_scheduler_token: str | None = Header(default=None)):
    if not settings.scheduler_token or x_scheduler_token != settings.scheduler_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler token")
    return await scanner.run_once()


@app.post("/internal/ml/train")
async def train_ml(x_scheduler_token: str | None = Header(default=None)):
    if not settings.scheduler_token or x_scheduler_token != settings.scheduler_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler token")
    return await learning_service.run_daily()
