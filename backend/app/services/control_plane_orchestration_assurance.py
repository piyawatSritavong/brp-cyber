from __future__ import annotations

import json
from typing import Any

from app.services.enterprise.objective_gate import OBJECTIVE_GATE_GLOBAL_HISTORY_STREAM
from app.services.redis_client import redis_client

GATE_NAMES = ("red", "blue", "purple", "closed_loop", "enterprise", "compliance")


def orchestration_objectives_status(limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrevrange(OBJECTIVE_GATE_GLOBAL_HISTORY_STREAM, count=max(1, limit))
    samples: list[dict[str, Any]] = []
    tenant_ids: set[str] = set()

    gate_pass_counts = {name: 0 for name in GATE_NAMES}
    overall_pass_count = 0

    for event_id, fields in entries:
        tenant_id = str(fields.get("tenant_id", ""))
        if tenant_id:
            tenant_ids.add(tenant_id)

        overall_pass = str(fields.get("overall_pass", "0")) == "1"
        if overall_pass:
            overall_pass_count += 1

        gates_raw = fields.get("gates", "{}")
        try:
            gates = json.loads(gates_raw)
        except json.JSONDecodeError:
            gates = {}

        sample_gates: dict[str, bool] = {}
        for gate_name in GATE_NAMES:
            passed = bool(gates.get(gate_name, {}).get("pass", False))
            sample_gates[gate_name] = passed
            if passed:
                gate_pass_counts[gate_name] += 1

        samples.append(
            {
                "id": event_id,
                "tenant_id": tenant_id,
                "overall_pass": overall_pass,
                "gates": sample_gates,
            }
        )

    sample_count = len(samples)
    gate_pass_rates = {
        name: round((gate_pass_counts[name] / sample_count) if sample_count else 0.0, 4)
        for name in GATE_NAMES
    }
    overall_pass_rate = round((overall_pass_count / sample_count) if sample_count else 0.0, 4)

    enterprise_ready = bool(
        sample_count > 0
        and overall_pass_rate >= 0.95
        and all(rate >= 0.95 for rate in gate_pass_rates.values())
    )

    return {
        "status": "ok",
        "sample_count": sample_count,
        "tenant_count": len(tenant_ids),
        "overall_pass_rate": overall_pass_rate,
        "gate_pass_rates": gate_pass_rates,
        "enterprise_readiness": {
            "ready": enterprise_ready,
            "criteria": {
                "overall_pass_rate_min": 0.95,
                "per_gate_pass_rate_min": 0.95,
            },
        },
        "rows": samples,
    }
