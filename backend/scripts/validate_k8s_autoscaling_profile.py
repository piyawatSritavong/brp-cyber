from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any


DEFAULT_NAMESPACE = "brp-cyber"
DEFAULT_DEPLOYMENT = "brp-scan-worker"
DEFAULT_HPA = "brp-scan-worker-hpa"
DEFAULT_SCALEDOBJECT = "brp-scan-worker-keda"
DEFAULT_CRONJOB = "brp-autoscaler-reconcile"
DEFAULT_MIN_REPLICAS = 2
DEFAULT_MAX_REPLICAS = 200
DEFAULT_STREAM_PREFIX = "scan_tasks:p"
DEFAULT_CONSUMER_GROUP = "scan-workers"
DEFAULT_RECONCILE_PATH = "/enterprise/autoscaler/reconcile"


def _kubectl_json(
    kind: str,
    name: str,
    *,
    namespace: str,
    kubectl: str,
    context: str | None,
) -> dict[str, Any]:
    command = [kubectl]
    if context:
        command.extend(["--context", context])
    command.extend(["-n", namespace, "get", kind, name, "-o", "json"])
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    return payload if isinstance(payload, dict) else {}


def _nested(payload: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def _append_check(checks: list[dict[str, Any]], name: str, ok: bool, details: str) -> None:
    checks.append({"name": name, "ok": ok, "details": details})


def validate_cluster_profile(
    *,
    namespace: str = DEFAULT_NAMESPACE,
    kubectl: str = "kubectl",
    context: str | None = None,
    deployment_name: str = DEFAULT_DEPLOYMENT,
    hpa_name: str = DEFAULT_HPA,
    scaledobject_name: str = DEFAULT_SCALEDOBJECT,
    cronjob_name: str = DEFAULT_CRONJOB,
) -> dict[str, Any]:
    deployment = _kubectl_json("deployment", deployment_name, namespace=namespace, kubectl=kubectl, context=context)
    hpa = _kubectl_json("hpa", hpa_name, namespace=namespace, kubectl=kubectl, context=context)
    scaledobject = _kubectl_json(
        "scaledobject",
        scaledobject_name,
        namespace=namespace,
        kubectl=kubectl,
        context=context,
    )
    cronjob = _kubectl_json("cronjob", cronjob_name, namespace=namespace, kubectl=kubectl, context=context)

    checks: list[dict[str, Any]] = []

    deployment_target = str(_nested(hpa, "spec", "scaleTargetRef", "name", default="") or "")
    _append_check(
        checks,
        "hpa_targets_worker_deployment",
        deployment_target == deployment_name,
        f"hpa_target={deployment_target or '<missing>'} expected={deployment_name}",
    )

    hpa_min_replicas = int(_nested(hpa, "spec", "minReplicas", default=0) or 0)
    hpa_max_replicas = int(_nested(hpa, "spec", "maxReplicas", default=0) or 0)
    _append_check(
        checks,
        "hpa_replica_bounds",
        hpa_min_replicas == DEFAULT_MIN_REPLICAS and hpa_max_replicas == DEFAULT_MAX_REPLICAS,
        f"min={hpa_min_replicas} max={hpa_max_replicas} expected_min={DEFAULT_MIN_REPLICAS} expected_max={DEFAULT_MAX_REPLICAS}",
    )

    scaledobject_target = str(_nested(scaledobject, "spec", "scaleTargetRef", "name", default="") or "")
    _append_check(
        checks,
        "scaledobject_targets_worker_deployment",
        scaledobject_target == deployment_name,
        f"scaledobject_target={scaledobject_target or '<missing>'} expected={deployment_name}",
    )

    scaledobject_min = int(_nested(scaledobject, "spec", "minReplicaCount", default=0) or 0)
    scaledobject_max = int(_nested(scaledobject, "spec", "maxReplicaCount", default=0) or 0)
    _append_check(
        checks,
        "scaledobject_replica_bounds",
        scaledobject_min == DEFAULT_MIN_REPLICAS and scaledobject_max == DEFAULT_MAX_REPLICAS,
        f"min={scaledobject_min} max={scaledobject_max} expected_min={DEFAULT_MIN_REPLICAS} expected_max={DEFAULT_MAX_REPLICAS}",
    )

    triggers = _nested(scaledobject, "spec", "triggers", default=[])
    if not isinstance(triggers, list):
        triggers = []
    redis_stream_trigger = next(
        (
            trigger
            for trigger in triggers
            if isinstance(trigger, dict) and str(trigger.get("type", "") or "") == "redis-streams"
        ),
        {},
    )
    trigger_metadata = redis_stream_trigger.get("metadata", {}) if isinstance(redis_stream_trigger, dict) else {}
    trigger_stream = str(trigger_metadata.get("stream", "") or "")
    trigger_consumer_group = str(trigger_metadata.get("consumerGroup", "") or "")
    _append_check(
        checks,
        "scaledobject_redis_stream_trigger",
        trigger_stream.startswith(DEFAULT_STREAM_PREFIX) and trigger_consumer_group == DEFAULT_CONSUMER_GROUP,
        f"stream={trigger_stream or '<missing>'} consumer_group={trigger_consumer_group or '<missing>'}",
    )

    container_specs = _nested(deployment, "spec", "template", "spec", "containers", default=[])
    if not isinstance(container_specs, list):
        container_specs = []
    worker_container = next(
        (
            container
            for container in container_specs
            if isinstance(container, dict) and str(container.get("name", "") or "") == "scan-worker"
        ),
        {},
    )
    container_command = [str(part) for part in worker_container.get("command", [])] if isinstance(worker_container, dict) else []
    _append_check(
        checks,
        "worker_command_targets_scan_worker",
        "app.workers.scan_worker" in container_command,
        f"command={container_command or ['<missing>']}",
    )

    desired_replicas = int(_nested(deployment, "spec", "replicas", default=0) or 0)
    ready_replicas = int(_nested(deployment, "status", "readyReplicas", default=0) or 0)
    _append_check(
        checks,
        "worker_ready_replicas_meet_minimum",
        ready_replicas >= min(DEFAULT_MIN_REPLICAS, max(desired_replicas, 1)),
        f"ready={ready_replicas} desired={desired_replicas}",
    )

    cron_schedule = str(_nested(cronjob, "spec", "schedule", default="") or "")
    cron_containers = _nested(cronjob, "spec", "jobTemplate", "spec", "template", "spec", "containers", default=[])
    if not isinstance(cron_containers, list):
        cron_containers = []
    cron_args: list[str] = []
    for container in cron_containers:
        if isinstance(container, dict):
            cron_args.extend(str(part) for part in container.get("args", []))
    _append_check(
        checks,
        "autoscaler_reconcile_cronjob_endpoint",
        cron_schedule == "*/1 * * * *" and any(DEFAULT_RECONCILE_PATH in value for value in cron_args),
        f"schedule={cron_schedule or '<missing>'} args={cron_args or ['<missing>']}",
    )

    failures = [check for check in checks if not check["ok"]]

    return {
        "ok": not failures,
        "namespace": namespace,
        "context": context or "",
        "resources": {
            "deployment": deployment_name,
            "hpa": hpa_name,
            "scaledobject": scaledobject_name,
            "cronjob": cronjob_name,
        },
        "status": {
            "worker_desired_replicas": desired_replicas,
            "worker_ready_replicas": ready_replicas,
            "hpa_current_replicas": int(_nested(hpa, "status", "currentReplicas", default=0) or 0),
            "hpa_desired_replicas": int(_nested(hpa, "status", "desiredReplicas", default=0) or 0),
            "scaledobject_original_replica_count": int(
                _nested(scaledobject, "status", "originalReplicaCount", default=0) or 0
            ),
        },
        "checks": checks,
        "failures": [check["name"] for check in failures],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate deployed KEDA/HPA autoscaling profile on a target cluster")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--kubectl", default="kubectl")
    parser.add_argument("--context")
    parser.add_argument("--deployment", default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--hpa", default=DEFAULT_HPA)
    parser.add_argument("--scaledobject", default=DEFAULT_SCALEDOBJECT)
    parser.add_argument("--cronjob", default=DEFAULT_CRONJOB)
    args = parser.parse_args()

    result = validate_cluster_profile(
        namespace=args.namespace,
        kubectl=args.kubectl,
        context=args.context,
        deployment_name=args.deployment,
        hpa_name=args.hpa,
        scaledobject_name=args.scaledobject,
        cronjob_name=args.cronjob,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
