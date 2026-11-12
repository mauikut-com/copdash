"""Pydantic models — the single source of truth for validation and OpenAPI.

Every request and response shape lives here, with field descriptions and
examples so the auto-generated ``/docs`` and ``/openapi.json`` are usable
immediately.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Request: server spec (capacity)
# --------------------------------------------------------------------------- #


class CpuSpec(BaseModel):
    """CPU capacity of the server."""

    cores: float = Field(..., gt=0, description="Number of CPU cores available.", examples=[4])
    clock_ghz: float = Field(
        ...,
        gt=0,
        description=(
            "Clock speed per core, in GHz. Reserved for the future simulation "
            "engine; the rules engine keys off core count only."
        ),
        examples=[2.5],
    )


class RamSpec(BaseModel):
    """RAM capacity of the server."""

    total_mb: float = Field(..., gt=0, description="Total RAM, in megabytes.", examples=[8192])


class NetworkSpec(BaseModel):
    """Network capacity of the server."""

    bandwidth_mbps: float = Field(
        ..., gt=0, description="Bandwidth capacity, in megabits per second.", examples=[1000]
    )
    max_connections: int = Field(
        ..., gt=0, description="Maximum number of concurrent connections.", examples=[10000]
    )


class ServerSpec(BaseModel):
    """The server's hardware capacity."""

    cpu: CpuSpec
    ram: RamSpec
    network: NetworkSpec


# --------------------------------------------------------------------------- #
# Request: load (demand)
# --------------------------------------------------------------------------- #


class Load(BaseModel):
    """The projected load to evaluate against the spec."""

    rps: float = Field(..., ge=0, description="Requests per second.", examples=[500])
    avg_cpu_ms_per_req: float = Field(
        ..., ge=0, description="Average CPU time per request, in milliseconds.", examples=[3.0]
    )
    avg_mem_mb_per_req: float = Field(
        ...,
        ge=0,
        description="Average memory held per concurrent request, in megabytes.",
        examples=[2.0],
    )
    concurrent_connections: int = Field(
        ..., ge=0, description="Number of concurrent connections (drives RAM and connection pressure).", examples=[250]
    )
    payload_kb: float = Field(
        ..., ge=0, description="Response payload size per request, in kilobytes.", examples=[20.0]
    )


# --------------------------------------------------------------------------- #
# Request / response envelopes
# --------------------------------------------------------------------------- #


class VerdictRequest(BaseModel):
    """Body for ``POST /verdict``."""

    engine: str = Field("rules", description="Engine to evaluate with. Defaults to 'rules'.", examples=["rules"])
    spec: ServerSpec
    load: Load


class EvaluationInput(BaseModel):
    """The input handed to ``VerdictEngine.evaluate()``."""

    spec: ServerSpec
    load: Load


# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #

Verdict = Literal["will_crash", "will_survive", "at_risk"]
ResourceName = Literal["cpu", "ram", "network"]
ResourceStatus = Literal["ok", "warning", "critical"]


class ResourceUtilization(BaseModel):
    """A single resource's demand/capacity projection."""

    utilization: float = Field(
        ..., description="Demand / capacity ratio; 1.0 means 100% of capacity.", examples=[0.75]
    )
    status: ResourceStatus = Field(
        ...,
        description="'ok' (< 80%), 'warning' (80-100%), or 'critical' (> 100%).",
        examples=["ok"],
    )


class ResourceSummary(BaseModel):
    """Utilization for each of the three resources."""

    cpu: ResourceUtilization
    ram: ResourceUtilization
    network: ResourceUtilization


class VerdictResult(BaseModel):
    """The core output of a verdict engine (without the engine label)."""

    verdict: Verdict = Field(..., description="Overall verdict.", examples=["will_survive"])
    confidence: float = Field(
        ..., ge=0, le=1, description="How decisive the verdict is, from 0 to 1.", examples=[0.9]
    )
    bottleneck: ResourceName | None = Field(
        ...,
        description="Resource with the highest utilization, or null when there is no load.",
        examples=["cpu"],
    )
    resources: ResourceSummary
    reasons: list[str] = Field(default_factory=list, description="Human-readable derivation steps.")


class VerdictResponse(VerdictResult):
    """Full ``POST /verdict`` response, including the engine that produced it."""

    engine: str = Field(..., description="Engine that produced the verdict.", examples=["rules"])


class EnginesResponse(BaseModel):
    """Body for ``GET /engines``."""

    engines: list[str] = Field(..., description="Names of available engines.", examples=[["rules"]])
