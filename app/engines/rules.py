"""The rules engine: a deterministic, formula-based verdict.

All demand/capacity formulas live in this one file so they can be reviewed and
tuned in a single place. Utilization is demand / capacity per resource:

    cpu:     demand   = rps * avg_cpu_ms_per_req / 1000        (busy cores)
             capacity = spec.cpu.cores
    ram:     demand   = concurrent_connections * avg_mem_mb_per_req   (MB)
             capacity = spec.ram.total_mb
    network: two independent constraints; take the stricter (max):
             bandwidth demand  = rps * payload_kb * 8 / 1000   (Mbps)
             connection demand = concurrent_connections / max_connections

The overall verdict is driven by the peak utilization across resources:

    > 100%     -> will_crash
    80% - 100% -> at_risk
    < 80%      -> will_survive

The bottleneck is the resource with the highest utilization.
"""

from __future__ import annotations

from typing import Literal

from app.schemas import (
    EvaluationInput,
    ResourceSummary,
    ResourceUtilization,
    VerdictResult,
)

# Decision thresholds, expressed as utilization ratios (1.0 == 100%).
AT_RISK_THRESHOLD = 0.8
CRASH_THRESHOLD = 1.0


class RulesEngine:
    """Deterministic, rule-based verdict engine."""

    name = "rules"

    def evaluate(self, input: EvaluationInput) -> VerdictResult:
        spec = input.spec
        load = input.load

        # --- CPU ----------------------------------------------------------- #
        # Each request costs avg_cpu_ms_per_req ms of CPU. At rps requests per
        # second, the server spends (rps * ms / 1000) core-seconds per second,
        # i.e. that many cores are kept busy.
        cpu_demand = load.rps * load.avg_cpu_ms_per_req / 1000.0
        cpu_capacity = spec.cpu.cores
        cpu_util = cpu_demand / cpu_capacity

        # --- RAM ----------------------------------------------------------- #
        # Memory scales with concurrent connections, not raw rps: each in-flight
        # request holds avg_mem_mb_per_req MB.
        ram_demand = load.concurrent_connections * load.avg_mem_mb_per_req
        ram_capacity = spec.ram.total_mb
        ram_util = ram_demand / ram_capacity

        # --- Network ------------------------------------------------------- #
        # Bandwidth: each request returns payload_kb KB = payload_kb * 8 kbit.
        # rps requests/s therefore need (rps * payload_kb * 8 / 1000) Mbit/s.
        net_bw_demand = load.rps * load.payload_kb * 8.0 / 1000.0
        net_bw_util = net_bw_demand / spec.network.bandwidth_mbps
        # Connections: concurrent connections against the connection limit.
        net_conn_util = load.concurrent_connections / spec.network.max_connections
        # The stricter of the two network constraints governs network health.
        net_util = max(net_bw_util, net_conn_util)

        utilizations = {
            "cpu": cpu_util,
            "ram": ram_util,
            "network": net_util,
        }
        peak = max(utilizations.values())

        # --- Verdict ------------------------------------------------------- #
        if peak > CRASH_THRESHOLD:
            verdict = "will_crash"
        elif peak >= AT_RISK_THRESHOLD:
            verdict = "at_risk"
        else:
            verdict = "will_survive"

        bottleneck = max(utilizations, key=utilizations.get) if peak > 0 else None

        resources = ResourceSummary(
            cpu=ResourceUtilization(utilization=round(cpu_util, 4), status=_status(cpu_util)),
            ram=ResourceUtilization(utilization=round(ram_util, 4), status=_status(ram_util)),
            network=ResourceUtilization(utilization=round(net_util, 4), status=_status(net_util)),
        )

        reasons = [
            f"CPU: {cpu_demand:.2f} of {cpu_capacity:.2f} cores busy ({cpu_util:.1%}).",
            f"RAM: {ram_demand:.0f} of {ram_capacity:.0f} MB used ({ram_util:.1%}).",
            (
                f"Network: {net_bw_demand:.1f} Mbps bandwidth ({net_bw_util:.1%}), "
                f"{load.concurrent_connections}/{spec.network.max_connections} connections "
                f"({net_conn_util:.1%})."
            ),
        ]
        if bottleneck is None:
            reasons.append("No load: every resource is idle.")
        else:
            reasons.append(
                f"Peak utilization {peak:.1%} on {bottleneck}; verdict {verdict}."
            )

        return VerdictResult(
            verdict=verdict,
            confidence=_confidence(peak, verdict),
            bottleneck=bottleneck,
            resources=resources,
            reasons=reasons,
        )


def _status(utilization: float) -> Literal["ok", "warning", "critical"]:
    """Per-resource status from its utilization."""
    if utilization > CRASH_THRESHOLD:
        return "critical"
    if utilization >= AT_RISK_THRESHOLD:
        return "warning"
    return "ok"


def _confidence(peak: float, verdict: str) -> float:
    """A deterministic 0..1 confidence, higher the further from a boundary.

    Boundaries sit at 0.8 (survive -> at_risk) and 1.0 (at_risk -> crash).
    """
    if verdict == "will_survive":
        # peak in [0, 0.8): 1.0 at no load, falling to 0.5 at the boundary.
        value = 1.0 - (peak / AT_RISK_THRESHOLD) * 0.5
    elif verdict == "at_risk":
        # peak in [0.8, 1.0]: most confident at the band midpoint (0.9).
        value = 1.0 - abs(peak - 0.9) / 0.1 * 0.5
    else:  # will_crash
        # peak > 1.0: grows toward 1.0 the further over capacity.
        value = min(1.0, 0.5 + (peak - CRASH_THRESHOLD))
    return round(value, 2)
