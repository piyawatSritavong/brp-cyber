from __future__ import annotations

import sys

import pytest

from scripts import validate_k8s_autoscaling_profile


def test_validate_cluster_profile_passes_with_consistent_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = {
        ("deployment", "brp-scan-worker"): {
            "spec": {
                "replicas": 4,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "scan-worker",
                                "command": ["python", "-m", "app.workers.scan_worker"],
                            }
                        ]
                    }
                },
            },
            "status": {"readyReplicas": 4},
        },
        ("hpa", "brp-scan-worker-hpa"): {
            "spec": {
                "scaleTargetRef": {"name": "brp-scan-worker"},
                "minReplicas": 2,
                "maxReplicas": 200,
            },
            "status": {"currentReplicas": 4, "desiredReplicas": 4},
        },
        ("scaledobject", "brp-scan-worker-keda"): {
            "spec": {
                "scaleTargetRef": {"name": "brp-scan-worker"},
                "minReplicaCount": 2,
                "maxReplicaCount": 200,
                "triggers": [
                    {
                        "type": "redis-streams",
                        "metadata": {
                            "stream": "scan_tasks:p0",
                            "consumerGroup": "scan-workers",
                        },
                    }
                ],
            },
            "status": {"originalReplicaCount": 4},
        },
        ("cronjob", "brp-autoscaler-reconcile"): {
            "spec": {
                "schedule": "*/1 * * * *",
                "jobTemplate": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "args": [
                                            "/bin/sh",
                                            "-c",
                                            'curl -s -X POST "http://brp-api/enterprise/autoscaler/reconcile" > /dev/null',
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                },
            }
        },
    }

    def fake_kubectl_json(kind: str, name: str, *, namespace: str, kubectl: str, context: str | None):
        assert namespace == "brp-cyber"
        assert kubectl == "kubectl"
        assert context is None
        return fixtures[(kind, name)]

    monkeypatch.setattr(validate_k8s_autoscaling_profile, "_kubectl_json", fake_kubectl_json)

    result = validate_k8s_autoscaling_profile.validate_cluster_profile()

    assert result["ok"] is True
    assert result["failures"] == []
    assert result["status"]["worker_ready_replicas"] == 4


def test_validate_cluster_profile_reports_wiring_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = {
        ("deployment", "brp-scan-worker"): {
            "spec": {
                "replicas": 4,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "scan-worker",
                                "command": ["python", "-m", "app.workers.other_worker"],
                            }
                        ]
                    }
                },
            },
            "status": {"readyReplicas": 1},
        },
        ("hpa", "brp-scan-worker-hpa"): {
            "spec": {
                "scaleTargetRef": {"name": "wrong-deployment"},
                "minReplicas": 1,
                "maxReplicas": 10,
            },
            "status": {"currentReplicas": 1, "desiredReplicas": 2},
        },
        ("scaledobject", "brp-scan-worker-keda"): {
            "spec": {
                "scaleTargetRef": {"name": "wrong-deployment"},
                "minReplicaCount": 1,
                "maxReplicaCount": 10,
                "triggers": [
                    {
                        "type": "redis-streams",
                        "metadata": {
                            "stream": "wrong_stream",
                            "consumerGroup": "wrong-group",
                        },
                    }
                ],
            },
            "status": {"originalReplicaCount": 1},
        },
        ("cronjob", "brp-autoscaler-reconcile"): {
            "spec": {
                "schedule": "*/5 * * * *",
                "jobTemplate": {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [{"args": ["/bin/sh", "-c", "echo nope"]}]
                            }
                        }
                    }
                },
            }
        },
    }

    monkeypatch.setattr(
        validate_k8s_autoscaling_profile,
        "_kubectl_json",
        lambda kind, name, *, namespace, kubectl, context: fixtures[(kind, name)],
    )

    result = validate_k8s_autoscaling_profile.validate_cluster_profile()

    assert result["ok"] is False
    assert "hpa_targets_worker_deployment" in result["failures"]
    assert "scaledobject_targets_worker_deployment" in result["failures"]
    assert "scaledobject_redis_stream_trigger" in result["failures"]
    assert "worker_command_targets_scan_worker" in result["failures"]
    assert "autoscaler_reconcile_cronjob_endpoint" in result["failures"]


def test_main_exits_nonzero_when_validation_fails(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        validate_k8s_autoscaling_profile,
        "validate_cluster_profile",
        lambda **_kwargs: {"ok": False, "failures": ["example"], "checks": []},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["validate_k8s_autoscaling_profile.py"],
    )

    with pytest.raises(SystemExit) as excinfo:
        validate_k8s_autoscaling_profile.main()

    assert excinfo.value.code == 1
    assert '"ok": false' in capsys.readouterr().out.lower()
