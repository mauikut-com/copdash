"""The SimPy engine: a minimal discrete-event simulation of the three resource
blocks (CPU, RAM, network) behind the same ``VerdictEngine`` interface as the
rules engine.

Requests arrive as a Poisson process at ``load.rps`` and flow through three
SimPy primitives:

    network  — a ``Resource`` of ``max_connections`` slots (one per request)
    ram      — a ``Container`` holding ``total_mb``; each request draws
               ``avg_mem_mb_per_req`` for its lifetime
    cpu      — a ``Resource`` of ``ceil(cores)`` cores; each request holds one
               core for ``avg_cpu_ms_per_req`` ms, then ships its payload over
               the wire (``payload_kb`` at ``bandwidth_mbps``) with the core
               released

The simulation *measures* time-averaged utilization of each block. Because a
saturated resource is simply busy ~100% of the time, its measured utilization
caps near 1.0 and can't express "150% overloaded". So when a resource is
oversubscribed the engine reports the closed-form *offered* ratio instead
(identical to the rules engine's demand/capacity formulas), keeping the
overload magnitude and the verdict comparable to the rules engine.

A fixed seed and horizon make the verdict reproducible for a given input.
"""

from __future__ import annotations

import math
import random
from typing import Literal

import simpy

from app.schemas import (
    EvaluationInput,
    ResourceSummary,
    ResourceUtilization,
    VerdictResult,
)

# Decision thresholds, shared with the rules engine (1.0 == 100%).
AT_RISK_THRESHOLD = 0.8
CRASH_THRESHOLD = 1.0

# Simulation controls. Bounded so a single verdict stays fast even at high rps.
HORIZON = 30.0  # simulated seconds per run
SEED = 0        # fixed for reproducibility
MAX_ARRIVALS = 20_000


class SimPyEngine:
    """Discrete-event verdict engine using SimPy resource blocks."""

    name = "simpy"

    def evaluate(self, input: EvaluationInput) -> VerdictResult:
        spec = input.spec
        load = input.load

        env = simpy.Environment()

        # --- The three blocks ------------------------------------------------- #
        cpu_capacity = max(1, math.ceil(spec.cpu.cores))
        cpu = simpy.Resource(env, capacity=cpu_capacity)
        ram = simpy.Container(env, init=spec.ram.total_mb, capacity=spec.ram.total_mb)
        net = simpy.Resource(env, capacity=spec.network.max_connections)

        # --- Accumulators ----------------------------------------------------- #
        stats = {
            "arrived": 0,
            "completed": 0,
            "cpu_busy": 0.0,   # core-seconds of CPU work
            "ram_busy": 0.0,   # MB-seconds of memory held
            "net_busy": 0.0,   # connection-seconds held
            "bytes": 0.0,      # KB shipped
        }

        def request() -> None:
            cpu_time = load.avg_cpu_ms_per_req / 1000.0
            wire_time = load.payload_kb * 8.0 / (spec.network.bandwidth_mbps * 1000.0)
            mem_hold = load.avg_mem_mb_per_req

            with net.request() as conn_req:
                yield conn_req
                conn_acquired = env.now
                yield ram.get(mem_hold)
                mem_acquired = env.now
                try:
                    with cpu.request() as cpu_req:
                        yield cpu_req
                        yield env.timeout(cpu_time)
                        stats["cpu_busy"] += cpu_time
                    # Wire transfer: connection + memory still held, core released.
                    yield env.timeout(wire_time)
                finally:
                    yield ram.put(mem_hold)
                stats["ram_busy"] += mem_hold * (env.now - mem_acquired)
            stats["net_busy"] += env.now - conn_acquired
            stats["bytes"] += load.payload_kb
            stats["completed"] += 1

        # Number of arrivals to simulate: enough to fill a HORIZON-second
        # arrival window, capped so a single verdict stays fast at high rps.
        arrivals_count = (
            min(MAX_ARRIVALS, max(1, int(load.rps * HORIZON)))
            if load.rps > 0
            else 0
        )

        def arrivals() -> None:
            rng = random.Random(SEED)
            for _ in range(arrivals_count):
                yield env.timeout(rng.expovariate(load.rps))
                stats["arrived"] += 1
                env.process(request())

        env.process(arrivals())
        # Run to natural completion: arrivals are finite, so the queue drains and
        # no request generator is left suspended (avoids GeneratorExit on GC).
        env.run()
        horizon = env.now or 1.0  # 1.0 guard for the no-load case (now == 0)

        # --- Measured (time-averaged) utilization ----------------------------- #
        cpu_measured = stats["cpu_busy"] / (cpu_capacity * horizon)
        ram_measured = stats["ram_busy"] / (spec.ram.total_mb * horizon)
        bw_measured = (
            stats["bytes"] * 8.0 / 1000.0 / horizon / spec.network.bandwidth_mbps
        )
        conn_measured = stats["net_busy"] / (spec.network.max_connections * horizon)

        # --- Offered (closed-form) utilization, matching the rules engine ------ #
        # Used only to report overload magnitude when a block is oversubscribed,
        # since the measured value saturates at ~100%.
        offered_cpu = (load.rps * load.avg_cpu_ms_per_req / 1000.0) / spec.cpu.cores
        offered_ram = (load.concurrent_connections * load.avg_mem_mb_per_req) / spec.ram.total_mb
        offered_bw = (load.rps * load.payload_kb * 8.0 / 1000.0) / spec.network.bandwidth_mbps
        offered_conn = load.concurrent_connections / spec.network.max_connections

        cpu_util = _util(cpu_measured, offered_cpu)
        ram_util = _util(ram_measured, offered_ram)
        net_bw_util = _util(bw_measured, offered_bw)
        net_conn_util = _util(conn_measured, offered_conn)
        net_util = max(net_bw_util, net_conn_util)

        utilizations = {"cpu": cpu_util, "ram": ram_util, "network": net_util}
        peak = max(utilizations.values())

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
            (
                f"SimPy: {stats['arrived']} requests arrived, {stats['completed']} "
                f"completed over {horizon:.1f}s (seed {SEED})."
            ),
            f"CPU: {cpu_util:.1%} of {cpu_capacity} cores (offered {offered_cpu:.1%}).",
            f"RAM: {ram_util:.1%} of {spec.ram.total_mb:.0f} MB (offered {offered_ram:.1%}).",
            (
                f"Network: {net_bw_util:.1%} bandwidth ({bw_measured:.1%} measured), "
                f"{net_conn_util:.1%} connections ({conn_measured:.1%} measured)."
            ),
        ]
        if bottleneck is None:
            reasons.append("No load: every resource is idle.")
        else:
            reasons.append(f"Peak utilization {peak:.1%} on {bottleneck}; verdict {verdict}.")

        return VerdictResult(
            verdict=verdict,
            confidence=_confidence(peak, verdict),
            bottleneck=bottleneck,
            resources=resources,
            reasons=reasons,
        )


def _util(measured: float, offered: float) -> float:
    """Report offered when oversubscribed (measured saturates near 100%),
    otherwise the measured time-average."""
    return offered if offered > CRASH_THRESHOLD else measured


def _status(utilization: float) -> Literal["ok", "warning", "critical"]:
    """Per-resource status from its utilization (mirrors rules.py)."""
    if utilization > CRASH_THRESHOLD:
        return "critical"
    if utilization >= AT_RISK_THRESHOLD:
        return "warning"
    return "ok"


def _confidence(peak: float, verdict: str) -> float:
    """A deterministic 0..1 confidence, higher the further from a boundary
    (mirrors rules.py)."""
    if verdict == "will_survive":
        value = 1.0 - (peak / AT_RISK_THRESHOLD) * 0.5
    elif verdict == "at_risk":
        value = 1.0 - abs(peak - 0.9) / 0.1 * 0.5
    else:  # will_crash
        value = min(1.0, 0.5 + (peak - CRASH_THRESHOLD))
    return round(value, 2)
