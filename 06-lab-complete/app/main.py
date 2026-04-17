"""
Production AI Agent — Kết hợp tất cả Day 12 concepts

Checklist:
  ✅ Config từ environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication
  ✅ Rate limiting
  ✅ Cost guard
  ✅ Input validation (Pydantic)
  ✅ Health check + Readiness probe
  ✅ Graceful shutdown
  ✅ Security headers
  ✅ CORS
  ✅ Error handling
"""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import redis

from app.config import settings

# Mock LLM (thay bằng OpenAI/Anthropic khi có API key)
from utils.mock_llm import ask as llm_ask

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# ─────────────────────────────────────────────────────────
# Redis Client
# ─────────────────────────────────────────────────────────
# Kiểm tra định dạng URL (Phòng lỗi trên Cloud)
_redis_url = settings.redis_url
if not _redis_url or not any(_redis_url.startswith(s) for s in ["redis://", "rediss://", "unix://"]):
    logger.error(json.dumps({
        "event": "redis_config_error",
        "msg": f"Invalid REDIS_URL: '{_redis_url}'. Must start with redis://, rediss://, or unix://",
        "action": "Falling back to local mock storage (Not for production!)"
    }))
    # Tạo một mock client đơn giản nếu URL lỗi để app không crash
    class MockRedis:
        def get(self, *args, **kwargs): return None
        def setex(self, *args, **kwargs): pass
        def incr(self, *args, **kwargs): pass
        def expire(self, *args, **kwargs): pass
        def ping(self): return True
        def lrange(self, *args, **kwargs): return []
        def rpush(self, *args, **kwargs): pass
        def incrbyfloat(self, *args, **kwargs): pass
    r = MockRedis()
else:
    r = redis.from_url(_redis_url, decode_responses=True)

# ─────────────────────────────────────────────────────────
# Stateless Rate Limiter (Redis-based)
# ─────────────────────────────────────────────────────────
def check_rate_limit(user_key: str):
    # Dùng Fixed Window (đơn giản, hiệu quả)
    # Key format: rate:user_id:minute_timestamp
    now_minute = int(time.time() / 60)
    key = f"rate:{user_key}:{now_minute}"
    
    current = r.get(key)
    if current and int(current) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )
    
    # Tăng case và set expire sau 65s để tự dọn dẹp
    r.incr(key)
    r.expire(key, 65)

# ─────────────────────────────────────────────────────────
# Stateless Cost Guard (Redis-based)
# ─────────────────────────────────────────────────────────
def check_and_record_cost(user_id: str, input_tokens: int, output_tokens: int):
    today = time.strftime("%Y-%m-%d")
    key = f"cost:{user_id}:{today}"
    
    current_cost = float(r.get(key) or 0.0)
    if current_cost >= settings.daily_budget_usd:
        raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")
    
    new_cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    r.incrbyfloat(key, new_cost)
    r.expire(key, 36 * 3600)  # Giữ 36 tiếng cho chắc

# ─────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    try:
        r.ping()
        logger.info(json.dumps({"event": "redis_connected"}))
    except Exception as e:
        logger.error(json.dumps({"event": "redis_failed", "error": str(e)}))
    
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")
    session_id: str | None = Field(None, description="Conversation session ID")

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    Send a question to the AI agent.

    **Authentication:** Include header `X-API-Key: <your-key>`
    """
    # 1. Rate limit per API key
    check_rate_limit(_key[:8])

    # 2. Budget check
    input_tokens = len(body.question.split()) * 2
    check_and_record_cost(_key[:8], input_tokens, 0)

    # 3. Handle Session & History
    session_id = body.session_id or f"sess_{_key[:6]}"
    history_key = f"chat:{session_id}"
    
    # Lấy 10 câu gần nhất
    raw_history = r.lrange(history_key, -10, -1)
    history = [json.loads(m) for m in raw_history]

    logger.info(json.dumps({
        "event": "agent_call",
        "session_id": session_id,
        "history_len": len(history),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    # 4. Call LLM (với history bọc kèm - giả lập)
    answer = llm_ask(body.question)

    # 5. Save to History
    new_messages = [
        {"role": "user", "content": body.question},
        {"role": "assistant", "content": answer}
    ]
    for msg in new_messages:
        r.rpush(history_key, json.dumps(msg))
    r.expire(history_key, 3600)  # Hết hạn sau 1h không hoạt động

    # 6. Final cost recording (output)
    output_tokens = len(answer.split()) * 2
    check_and_record_cost(_key[:8], 0, output_tokens)

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts container if this fails."""
    status = "ok"
    checks = {"llm": "mock" if not settings.openai_api_key else "openai"}
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    try:
        r.ping()
    except:
        raise HTTPException(503, "Redis link down")
    return {"ready": True}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    today = time.strftime("%Y-%m-%d")
    current_cost = float(r.get(f"cost:{_key[:8]}:{today}") or 0.0)
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "daily_cost_usd": round(current_cost, 4),
        "daily_budget_usd": settings.daily_budget_usd,
        "budget_used_pct": round(current_cost / settings.daily_budget_usd * 100, 1),
    }


# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
