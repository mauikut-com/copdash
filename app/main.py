"""FastAPI application for server-verdict."""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.engines import ENGINES
from app.schemas import (
    EnginesResponse,
    EvaluationInput,
    VerdictRequest,
    VerdictResponse,
)

app = FastAPI(
    title="server-verdict",
    description="Will a server survive a given load? Deterministic, rule-based verdicts.",
    version="0.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_bearer = HTTPBearer(auto_error=False)


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """Optional Bearer-token auth. Enforced only when API_KEY is set."""
    expected = os.environ.get("API_KEY")
    if not expected:
        return
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@app.get(
    "/engines",
    response_model=EnginesResponse,
    dependencies=[Depends(require_api_key)],
)
def list_engines() -> EnginesResponse:
    """List the available verdict engines."""
    return EnginesResponse(engines=list(ENGINES))


@app.post(
    "/verdict",
    response_model=VerdictResponse,
    dependencies=[Depends(require_api_key)],
)
def verdict(request: VerdictRequest) -> VerdictResponse:
    """Evaluate a server spec against a load and return a verdict."""
    engine = ENGINES.get(request.engine)
    if engine is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown engine {request.engine!r}; available: {', '.join(ENGINES)}",
        )
    result = engine.evaluate(EvaluationInput(spec=request.spec, load=request.load))
    return VerdictResponse(**result.model_dump(), engine=engine.name)
