from __future__ import annotations

from typing import Any


ADAPTER_INVOKE_TEMPLATES: list[dict[str, Any]] = [
    {
        "source": "splunk",
        "vendor_preset_code": "splunk_notable_to_thai_triage",
        "display_name": "Splunk Alert to Blue Thai Alert Translator",
        "default_event_kind": "security_event",
        "recommended_plugin_codes": ["blue_thai_alert_translator", "blue_log_refiner"],
        "notes": [
            "Use this when Splunk Enterprise Security raises notable events that need Thai operator context.",
            "Payload is normalized through the OCSF-compatible integration layer before the plugin runs.",
        ],
        "activation_steps": [
            "Create an embedded endpoint bound to blue_thai_alert_translator for the target site.",
            "Store the returned X-BRP-Embed-Token in Splunk SOAR or webhook action secrets.",
            "Map notable-event fields such as src, dest, severity, and signature into the invoke payload below.",
        ],
        "automation_pack": {
            "workflow_type": "coworker_plugin",
            "default_playbook_code": "",
            "allowed_playbook_codes": [],
            "require_playbook_approval": True,
        },
        "field_mapping": [
            {"incoming": "src", "mapped_to": "actor.ip", "note": "Source IP of the alert"},
            {"incoming": "dest", "mapped_to": "target.resource", "note": "Target host or asset"},
            {"incoming": "severity/risk_level", "mapped_to": "severity", "note": "Mapped to low/medium/high"},
            {"incoming": "message/signature", "mapped_to": "message", "note": "Primary Thai summary context"},
        ],
        "invoke_payload": {
            "source": "splunk",
            "event_kind": "security_event",
            "dry_run": True,
            "actor": "splunk_soar",
            "payload": {
                "search_name": "ACB Brute Force Detection",
                "src": "203.0.113.20",
                "dest": "duck-sec-ai.vercel.app",
                "severity": "high",
                "signature": "Multiple failed admin login attempts",
                "message": "Excessive failed logins on admin login surface",
            },
        },
    },
    {
        "source": "crowdstrike",
        "vendor_preset_code": "crowdstrike_detection_to_managed_responder",
        "display_name": "CrowdStrike Detection to Managed AI Responder",
        "default_event_kind": "endpoint_detection",
        "recommended_plugin_codes": ["blue_auto_playbook_executor", "blue_thai_alert_translator"],
        "notes": [
            "Use this for Falcon detections that should trigger automated containment decisions.",
            "Combine with a Managed AI Responder policy if you want DB-backed response execution and SOAR dispatch.",
        ],
        "activation_steps": [
            "Create an embedded endpoint and choose CrowdStrike preset before saving.",
            "Use workflow_type=soar_playbook for direct containment or coworker_plugin for payload generation only.",
            "Set the playbook code to isolate-host-and-reset-session and keep allowed_playbook_codes narrow.",
            "Forward Falcon detection payloads through a webhook or custom action using the generated curl/header template.",
        ],
        "automation_pack": {
            "workflow_type": "soar_playbook",
            "default_playbook_code": "isolate-host-and-reset-session",
            "allowed_playbook_codes": ["isolate-host-and-reset-session", "notify-and-clear-session"],
            "require_playbook_approval": True,
        },
        "field_mapping": [
            {"incoming": "device.local_ip", "mapped_to": "actor.ip", "note": "Host IP used for containment context"},
            {"incoming": "device.hostname", "mapped_to": "target.resource", "note": "Endpoint host name"},
            {"incoming": "behavior.severity/severity", "mapped_to": "severity", "note": "Mapped to low/medium/high"},
            {"incoming": "description/behavior.description", "mapped_to": "message", "note": "Detection summary"},
        ],
        "invoke_payload": {
            "source": "crowdstrike",
            "event_kind": "endpoint_detection",
            "dry_run": True,
            "actor": "crowdstrike_falcon",
            "payload": {
                "device": {
                    "hostname": "ACB-LAPTOP-44",
                    "local_ip": "10.10.4.44",
                },
                "severity": "high",
                "description": "Suspicious credential dumping behavior detected",
                "behavior": {
                    "severity": "high",
                    "description": "LSASS access pattern matches credential access",
                },
            },
        },
    },
    {
        "source": "cloudflare",
        "vendor_preset_code": "cloudflare_waf_to_auto_playbook",
        "display_name": "Cloudflare WAF Event to Auto-Playbook Executor",
        "default_event_kind": "waf_event",
        "recommended_plugin_codes": ["blue_auto_playbook_executor", "blue_log_refiner"],
        "notes": [
            "Use this for WAF or Bot Management telemetry that should route into immediate WAF-tightening playbooks.",
            "Works well with embedded endpoints bound to blue_auto_playbook_executor or blue_log_refiner.",
        ],
        "activation_steps": [
            "Create a Cloudflare embedded endpoint and keep require_webhook_event_id enabled for replay safety.",
            "Use workflow_type=soar_playbook when you want Cloudflare telemetry to dispatch WAF containment directly.",
            "Use Logpush, Workers, or webhook forwarding to post WAF events to the generated invoke path.",
            "Lock allowed_playbook_codes to block-ip-and-waf-tighten for predictable containment.",
        ],
        "automation_pack": {
            "workflow_type": "soar_playbook",
            "default_playbook_code": "block-ip-and-waf-tighten",
            "allowed_playbook_codes": ["block-ip-and-waf-tighten"],
            "require_playbook_approval": True,
        },
        "field_mapping": [
            {"incoming": "ClientIP", "mapped_to": "actor.ip", "note": "Requester IP"},
            {"incoming": "ClientRequestURI", "mapped_to": "target.resource", "note": "Requested path"},
            {"incoming": "EdgeResponseStatus", "mapped_to": "severity", "note": "401/403/429 escalates to high"},
            {"incoming": "message/WAFAction", "mapped_to": "message", "note": "WAF decision context"},
        ],
        "invoke_payload": {
            "source": "cloudflare",
            "event_kind": "waf_event",
            "dry_run": True,
            "actor": "cloudflare_logpush",
            "payload": {
                "ClientIP": "198.51.100.77",
                "ClientRequestURI": "/admin-login",
                "EdgeResponseStatus": 403,
                "WAFAction": "managed_challenge",
                "message": "Cloudflare blocked suspicious login burst",
            },
        },
    },
]


def list_adapter_invoke_templates(*, source: str = "") -> dict[str, object]:
    normalized_source = str(source or "").strip().lower()
    rows = [
        row
        for row in ADAPTER_INVOKE_TEMPLATES
        if not normalized_source or row["source"] == normalized_source
    ]
    return {"count": len(rows), "rows": rows}
