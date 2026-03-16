from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    AiCoworkerPlugin,
    AiCoworkerPluginRun,
    BlueEventLog,
    PurpleInsightReport,
    RedScanRun,
    Site,
    SiteAiCoworkerPluginBinding,
)
from app.db.session import SessionLocal
from app.services.action_center import dispatch_manual_alert
from app.services.red_plugin_intelligence import (
    get_latest_red_plugin_intelligence,
    get_red_plugin_safety_policy,
)
from app.services.site_ops import generate_purple_executive_scorecard

BUILTIN_PLUGINS: list[dict[str, Any]] = [
    {
        "plugin_code": "red_exploit_code_generator",
        "display_name": "Exploit Code Generator",
        "display_name_th": "ผู้ช่วยสร้าง Exploit Python Script",
        "category": "red",
        "plugin_kind": "exploit_generator",
        "execution_mode": "manual",
        "description": "Converts recent vulnerability findings into a safe Python proof-of-concept script draft.",
        "value_statement": "ลดเวลาการแปลงรายงานช่องโหว่ให้เป็นโค้ดทดสอบเจาะระบบ และช่วยให้ทีม Red มีต้นแบบพร้อมใช้เร็วขึ้น",
        "default_config": {"target_surface": "/admin-login", "target_language": "python", "target_type": "web"},
    },
    {
        "plugin_code": "red_template_writer",
        "display_name": "Nuclei AI-Template Writer",
        "display_name_th": "ผู้ช่วยเขียน Nuclei AI-Template",
        "category": "red",
        "plugin_kind": "template_writer",
        "execution_mode": "manual",
        "description": "Builds a Nuclei YAML template draft from the latest findings and public attack signals.",
        "value_statement": "ช่วยให้ทีมสร้างตัวสแกนช่องโหว่ใหม่ได้ไวขึ้น และขยับไปสู่ protection within 1 hour",
        "default_config": {"target_surface": "/admin-login", "target_type": "web"},
    },
    {
        "plugin_code": "blue_log_refiner",
        "display_name": "AI Log Refiner (The Noise Killer)",
        "display_name_th": "AI Log Refiner (The Noise Killer)",
        "category": "blue",
        "plugin_kind": "log_refiner",
        "execution_mode": "scheduled",
        "description": "Filters noisy security logs and keeps the high-signal stream.",
        "value_statement": "กรอง log ขยะทิ้งและเหลือเฉพาะ alert ที่เสี่ยงจริง ช่วยลดภาระ SOC และลดต้นทุน storage ของระบบหลัก",
        "default_config": {"lookback_limit": 200, "max_signal_rows": 5},
    },
    {
        "plugin_code": "blue_thai_alert_translator",
        "display_name": "Thai Alert Translator & Summarizer",
        "display_name_th": "ปลั๊กอินแปลและสรุป Alert ภาษาไทย",
        "category": "blue",
        "plugin_kind": "translator",
        "execution_mode": "manual",
        "description": "Translates high-priority alerts into concise Thai incident context.",
        "value_statement": "ลดกำแพงด้านภาษาและเทคนิค ทำให้ทีม IT Support หรือ L1 อ่าน alert แล้วช่วยตอบสนองได้ทันที",
        "default_config": {"lookback_limit": 20, "max_alerts": 5},
    },
    {
        "plugin_code": "blue_auto_playbook_executor",
        "display_name": "Auto-Playbook Executor (Webhook)",
        "display_name_th": "ผู้ช่วยสั่ง Playbook อัตโนมัติผ่าน Webhook",
        "category": "blue",
        "plugin_kind": "webhook_executor",
        "execution_mode": "manual",
        "description": "Builds a one-click response playbook payload for firewall block, session clear, or isolation actions.",
        "value_statement": "เชื่อมเครื่องมือกระจัดกระจายเข้าด้วยกันและลดเวลาในการหยุดการโจมตีจากระดับนาทีเหลือระดับวินาที",
        "default_config": {"lookback_limit": 10, "max_actions": 3},
    },
    {
        "plugin_code": "purple_incident_ghostwriter",
        "display_name": "Incident Report Ghostwriter",
        "display_name_th": "ผู้ช่วยร่าง Incident Report",
        "category": "purple",
        "plugin_kind": "report_writer",
        "execution_mode": "manual",
        "description": "Drafts a Thai incident report from recent blue and purple evidence.",
        "value_statement": "ลดเวลาร่างรายงานเหตุการณ์จากหลักชั่วโมงเหลือหลักนาที",
        "default_config": {"blue_event_limit": 10},
    },
    {
        "plugin_code": "purple_mitre_heatmap",
        "display_name": "MITRE ATT&CK Heatmap Generator",
        "display_name_th": "ผู้ช่วยสร้าง MITRE ATT&CK Heatmap",
        "category": "purple",
        "plugin_kind": "heatmap",
        "execution_mode": "scheduled",
        "description": "Generates a MITRE ATT&CK heatmap summary from red and blue evidence.",
        "value_statement": "ทำให้ผู้บริหารเห็น blind spot ขององค์กรได้ทันทีโดยไม่ต้องไล่ข้อมูลหลายระบบ",
        "default_config": {"lookback_runs": 30, "lookback_events": 200, "sla_target_seconds": 120},
    },
]


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _safe_json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        payload = json.loads(value)
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def _safe_iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _normalize_category(value: str) -> str:
    category = str(value or "").strip().lower()
    return category[:32] or ""


def _normalize_channels(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        channel = str(raw or "").strip().lower()
        if not channel or channel in seen:
            continue
        seen.add(channel)
        normalized.append(channel[:32])
    return normalized


def _plugin_catalog_row(row: AiCoworkerPlugin) -> dict[str, Any]:
    return {
        "plugin_id": str(row.id),
        "plugin_code": row.plugin_code,
        "display_name": row.display_name,
        "display_name_th": row.display_name_th,
        "category": row.category,
        "plugin_kind": row.plugin_kind,
        "execution_mode": row.execution_mode,
        "description": row.description,
        "value_statement": row.value_statement,
        "default_config": _safe_json_dict(row.default_config_json),
        "is_active": bool(row.is_active),
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _binding_row(row: SiteAiCoworkerPluginBinding) -> dict[str, Any]:
    return {
        "binding_id": str(row.id),
        "site_id": str(row.site_id),
        "plugin_id": str(row.plugin_id),
        "enabled": bool(row.enabled),
        "auto_run": bool(row.auto_run),
        "schedule_interval_minutes": row.schedule_interval_minutes,
        "notify_channels": _safe_json_list(row.notify_channels_json),
        "config": _safe_json_dict(row.config_json),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _run_row(row: AiCoworkerPluginRun) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "plugin_id": str(row.plugin_id),
        "site_id": str(row.site_id),
        "status": row.status,
        "dry_run": bool(row.dry_run),
        "input_summary": _safe_json_dict(row.input_summary_json),
        "output_summary": _safe_json_dict(row.output_summary_json),
        "alert_routed": bool(row.alert_routed),
        "created_at": _safe_iso(row.created_at),
    }


def ensure_builtin_plugins(db: Session) -> dict[str, Any]:
    updated = 0
    created = 0
    now = datetime.now(timezone.utc)
    for builtin in BUILTIN_PLUGINS:
        existing = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == builtin["plugin_code"]))
        if existing:
            existing.display_name = builtin["display_name"]
            existing.display_name_th = builtin["display_name_th"]
            existing.category = builtin["category"]
            existing.plugin_kind = builtin["plugin_kind"]
            existing.execution_mode = builtin["execution_mode"]
            existing.description = builtin["description"]
            existing.value_statement = builtin["value_statement"]
            existing.default_config_json = _as_json(builtin["default_config"])
            existing.is_active = True
            existing.updated_at = now
            updated += 1
            continue

        row = AiCoworkerPlugin(
            plugin_code=builtin["plugin_code"],
            display_name=builtin["display_name"],
            display_name_th=builtin["display_name_th"],
            category=builtin["category"],
            plugin_kind=builtin["plugin_kind"],
            execution_mode=builtin["execution_mode"],
            description=builtin["description"],
            value_statement=builtin["value_statement"],
            default_config_json=_as_json(builtin["default_config"]),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        created += 1
    if created or updated:
        db.commit()
    return {"created_count": created, "updated_count": updated, "count": len(BUILTIN_PLUGINS)}


def list_coworker_plugins(db: Session, *, category: str = "", active_only: bool = True) -> dict[str, Any]:
    ensure_builtin_plugins(db)
    stmt = select(AiCoworkerPlugin).order_by(AiCoworkerPlugin.category, AiCoworkerPlugin.display_name)
    normalized_category = _normalize_category(category)
    if normalized_category:
        stmt = stmt.where(AiCoworkerPlugin.category == normalized_category)
    if active_only:
        stmt = stmt.where(AiCoworkerPlugin.is_active.is_(True))
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_plugin_catalog_row(row) for row in rows]}


def upsert_site_coworker_plugin_binding(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    enabled: bool,
    auto_run: bool,
    schedule_interval_minutes: int,
    notify_channels: list[str],
    config: dict[str, Any],
    owner: str,
) -> dict[str, Any]:
    ensure_builtin_plugins(db)
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == plugin_code))
    if not plugin:
        return {"status": "plugin_not_found", "plugin_code": plugin_code}

    row = db.scalar(
        select(SiteAiCoworkerPluginBinding).where(
            SiteAiCoworkerPluginBinding.site_id == site.id,
            SiteAiCoworkerPluginBinding.plugin_id == plugin.id,
        )
    )
    now = datetime.now(timezone.utc)
    if row:
        row.enabled = bool(enabled)
        row.auto_run = bool(auto_run)
        row.schedule_interval_minutes = max(5, min(int(schedule_interval_minutes), 1440))
        row.notify_channels_json = _as_json(_normalize_channels(notify_channels))
        row.config_json = _as_json(config)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "plugin": _plugin_catalog_row(plugin), "binding": _binding_row(row)}

    created = SiteAiCoworkerPluginBinding(
        site_id=site.id,
        plugin_id=plugin.id,
        enabled=bool(enabled),
        auto_run=bool(auto_run),
        schedule_interval_minutes=max(5, min(int(schedule_interval_minutes), 1440)),
        notify_channels_json=_as_json(_normalize_channels(notify_channels)),
        config_json=_as_json(config),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "plugin": _plugin_catalog_row(plugin), "binding": _binding_row(created)}


def list_site_coworker_plugins(db: Session, *, site_id: UUID, category: str = "") -> dict[str, Any]:
    ensure_builtin_plugins(db)
    site = db.get(Site, site_id)
    if not site:
        return {"count": 0, "rows": []}

    plugins = list_coworker_plugins(db, category=category, active_only=True)["rows"]
    bindings = db.scalars(
        select(SiteAiCoworkerPluginBinding).where(SiteAiCoworkerPluginBinding.site_id == site.id)
    ).all()
    binding_by_plugin_id = {str(binding.plugin_id): binding for binding in bindings}
    rows: list[dict[str, Any]] = []
    for plugin in plugins:
        binding = binding_by_plugin_id.get(plugin["plugin_id"])
        rows.append(
            {
                **plugin,
                "installed": binding is not None,
                "binding": _binding_row(binding) if binding else None,
            }
        )
    return {"site_id": str(site.id), "count": len(rows), "rows": rows}


def _severity_from_events(rows: list[BlueEventLog]) -> str:
    if any(row.ai_severity == "high" for row in rows):
        return "high"
    if any(row.ai_severity == "medium" for row in rows):
        return "medium"
    return "low"


def _recommendation_th(code: str) -> str:
    mapping = {
        "block_ip": "ควรบล็อก IP ต้นทางทันทีและตรวจสอบว่ามีการพยายามซ้ำหรือไม่",
        "notify_team": "ควรแจ้งทีมที่เกี่ยวข้องเพื่อตรวจสอบต่อทันที",
        "limit_user": "ควรจำกัดสิทธิ์หรือบังคับ reset session ของผู้ใช้ที่เกี่ยวข้อง",
        "ignore": "ยังไม่ต้องตอบสนองเชิงรุก แต่ควรเฝ้าดูต่อ",
    }
    return mapping.get(code, "ควรตรวจสอบเพิ่มเติมโดยทีมปฏิบัติการ")


def _run_blue_log_refiner(db: Session, site: Site, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    lookback = max(10, min(int(config.get("lookback_limit", 200) or 200), 1000))
    max_rows = max(1, min(int(config.get("max_signal_rows", 5) or 5), 20))
    rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(lookback)
    ).all()
    risky = [row for row in rows if row.ai_severity in {"high", "medium"}]
    noise = [row for row in rows if row.ai_severity == "low"]
    total = len(rows)
    signal = len(risky)
    noise_ratio = round((len(noise) / total), 4) if total else 0.0
    summary_rows = [
        {
            "event_type": row.event_type,
            "severity": row.ai_severity,
            "source_ip": row.source_ip,
            "recommendation": row.ai_recommendation,
            "status": row.status,
        }
        for row in risky[:max_rows]
    ]
    input_summary = {"lookback_limit": lookback, "total_events": total}
    output_summary = {
        "headline": f"AI Log Refiner คัดสัญญาณสำคัญ {signal} จาก log {total} รายการ",
        "severity": "high" if signal >= 5 else ("medium" if signal >= 1 else "low"),
        "summary_th": (
            f"ระบบคัด noise ออก {len(noise)} รายการ เหลือ log ที่ควรไล่ต่อ {signal} รายการ "
            f"(noise reduction {round(noise_ratio * 100, 2)}%)"
        ),
        "metrics": {
            "total_events": total,
            "signal_events": signal,
            "noise_events": len(noise),
            "noise_reduction_ratio": noise_ratio,
        },
        "signal_rows": summary_rows,
    }
    return input_summary, output_summary


def _run_blue_thai_alert_translator(db: Session, site: Site, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    lookback = max(5, min(int(config.get("lookback_limit", 20) or 20), 100))
    max_alerts = max(1, min(int(config.get("max_alerts", 5) or 5), 20))
    rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(lookback)
    ).all()
    risky = [row for row in rows if row.ai_severity in {"high", "medium"}][:max_alerts]
    translated = [
        {
            "event_type": row.event_type,
            "severity": row.ai_severity,
            "summary_th": (
                f"พบเหตุการณ์ {row.event_type} จาก IP {row.source_ip} อยู่ในระดับ {row.ai_severity} "
                f"และระบบแนะนำให้ {row.ai_recommendation}"
            ),
            "action_th": _recommendation_th(row.ai_recommendation),
        }
        for row in risky
    ]
    input_summary = {"lookback_limit": lookback, "candidate_alerts": len(rows)}
    output_summary = {
        "headline": f"Thai Alert Translator & Summarizer สำหรับไซต์ {site.site_code}",
        "severity": _severity_from_events(risky) if risky else "low",
        "summary_th": "แปลและสรุป alert สำคัญเป็นภาษาไทย พร้อมบริบทและคำแนะนำที่คนทั่วไปในองค์กรอ่านแล้วนำไปใช้ต่อได้ทันที",
        "translated_alerts": translated,
    }
    return input_summary, output_summary


def _run_blue_auto_playbook_executor(db: Session, site: Site, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    lookback = max(5, min(int(config.get("lookback_limit", 10) or 10), 100))
    max_actions = max(1, min(int(config.get("max_actions", 3) or 3), 10))
    rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(lookback)
    ).all()
    candidate = next((row for row in rows if row.ai_severity in {"high", "medium"}), rows[0] if rows else None)
    if candidate is None:
        return {"lookback_limit": lookback}, {
            "headline": f"Auto-Playbook Executor ยังไม่มี event ให้ดำเนินการสำหรับ {site.site_code}",
            "severity": "low",
            "summary_th": "ยังไม่มี event ความเสี่ยงที่เหมาะสำหรับสร้าง playbook อัตโนมัติ",
            "playbook_steps": [],
            "webhook_payload": {},
        }

    recommended_action = candidate.ai_recommendation or "notify_team"
    actions = [
        {"step": "triage_event", "description": f"ยืนยันเหตุการณ์ {candidate.event_type} จาก {candidate.source_ip}"},
        {"step": recommended_action, "description": _recommendation_th(recommended_action)},
        {"step": "notify_team", "description": "แจ้งทีมที่เกี่ยวข้องพร้อมแนบบริบทภาษาไทย"},
    ][:max_actions]
    return {
        "lookback_limit": lookback,
        "candidate_event_type": candidate.event_type,
        "candidate_event_id": str(candidate.id),
    }, {
        "headline": f"Auto-Playbook Executor เตรียม webhook action สำหรับ {candidate.event_type}",
        "severity": candidate.ai_severity,
        "summary_th": "สร้าง payload สำหรับ one-click response เช่น block firewall, clear session หรือ isolate endpoint จาก event ล่าสุด",
        "playbook_steps": actions,
        "webhook_payload": {
            "site_code": site.site_code,
            "source_ip": candidate.source_ip,
            "event_type": candidate.event_type,
            "recommended_action": recommended_action,
            "steps": actions,
        },
    }


def _run_red_exploit_code_generator(db: Session, site: Site, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    target_surface = str(config.get("target_surface", "/admin-login") or "/admin-login")
    target_type = str(config.get("target_type", "web") or "web").strip().lower()[:32] or "web"
    target_language = str(config.get("target_language", "python") or "python").strip().lower()
    if target_language not in {"python", "bash", "curl"}:
        target_language = "python"
    latest_scan = db.scalar(
        select(RedScanRun)
        .where(RedScanRun.site_id == site.id)
        .order_by(desc(RedScanRun.created_at))
        .limit(1)
    )
    findings = _safe_json_dict(latest_scan.findings_json) if latest_scan else {}
    sensitive_paths = findings.get("sensitive_paths_open", []) if isinstance(findings.get("sensitive_paths_open"), list) else []
    if sensitive_paths:
        first_path = sensitive_paths[0]
        if isinstance(first_path, dict) and first_path.get("path"):
            target_surface = str(first_path["path"])
    intelligence = get_latest_red_plugin_intelligence(
        db,
        site_id=site.id,
        target_surface=target_surface,
        target_type=target_type,
    )
    safety_policy = get_red_plugin_safety_policy(db, site_id=site.id, target_type=target_type)["policy"]
    header_lines = []
    if safety_policy.get("require_comment_header", True):
        header_lines.append("# BRP Red Plugin Draft")
    if safety_policy.get("require_disclaimer", True):
        header_lines.append("# Authorized validation only. Do not use outside approved scope.")
    if intelligence and intelligence.get("cve_id"):
        header_lines.append(f"# Intelligence: {intelligence['cve_id']} | {intelligence.get('title', '')}")
    elif intelligence:
        header_lines.append(f"# Intelligence: {intelligence.get('source_type', 'article')} | {intelligence.get('title', '')}")

    base_url = site.base_url.rstrip("/")
    preview_by_language: dict[str, str] = {}
    for language in ("python", "bash", "curl"):
        comment_prefix = "#" if language in {"python", "bash", "curl"} else "#"
        lines = [line.replace("#", comment_prefix, 1) if line.startswith("#") else line for line in header_lines]
        lines.append("")
        if not safety_policy.get("allow_network_calls", True):
            if language == "python":
                lines.extend(
                    [
                        "SAFE_MODE = True",
                        f'BASE_URL = "{base_url}"',
                        f'PATH = "{target_surface}"',
                        'print("Network execution disabled by safety policy")',
                        'print(f"Review target manually: {BASE_URL}{PATH}")',
                    ]
                )
            elif language == "bash":
                lines.extend(
                    [
                        "SAFE_MODE=true",
                        f'BASE_URL="{base_url}"',
                        f'PATH="{target_surface}"',
                        'echo "Network execution disabled by safety policy"',
                        'echo "Review target manually: ${BASE_URL}${PATH}"',
                    ]
                )
            else:
                lines.extend(
                    [
                        f'# Review target manually: {base_url}{target_surface}',
                        "echo 'Network execution disabled by safety policy'",
                    ]
                )
        elif language == "python":
            lines.extend(
                [
                    "import requests",
                    "",
                    f'BASE_URL = "{base_url}"',
                    f'PATH = "{target_surface}"',
                    "",
                    "response = requests.get(f\"{BASE_URL}{PATH}\", timeout=10)",
                    "print(response.status_code)",
                    "print(response.text[:400])",
                ]
            )
        elif language == "bash":
            lines.extend(
                [
                    "set -euo pipefail",
                    f'BASE_URL="{base_url}"',
                    f'PATH="{target_surface}"',
                    'response_file="$(mktemp)"',
                    'status_code=$(curl -sS --max-time 10 -o "$response_file" -w "%{http_code}" "${BASE_URL}${PATH}")',
                    'echo "$status_code"',
                    'head -c 400 "$response_file"',
                    'rm -f "$response_file"',
                ]
            )
        else:
            lines.extend(
                [
                    f'curl -sS -D - "{base_url}{target_surface}" \\',
                    "  --max-time 10 | head -c 400",
                ]
            )
        preview_by_language[language] = "\n".join(lines)
    poc_preview = preview_by_language[target_language]
    input_summary = {
        "target_surface": target_surface,
        "target_type": target_type,
        "has_scan": latest_scan is not None,
        "sensitive_paths": len(sensitive_paths),
        "has_intelligence": intelligence is not None,
        "target_language": target_language,
    }
    output_summary = {
        "headline": f"Exploit Code Generator ร่าง {target_language} PoC สำหรับ {site.site_code}",
        "severity": "medium" if latest_scan is not None else "low",
        "summary_th": f"แปลง finding ล่าสุดให้เป็น {target_language} script เบื้องต้นสำหรับทดสอบเชิงยืนยันแบบปลอดภัยก่อนนำไปต่อยอดโดยทีม Red",
        "language": target_language,
        "script_preview": poc_preview,
        "script_variants": preview_by_language,
        "source_intelligence": intelligence or {},
        "target_type": target_type,
        "safety_policy": safety_policy,
    }
    return input_summary, output_summary


def _run_red_template_writer(db: Session, site: Site, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    target_surface = str(config.get("target_surface", "/admin-login") or "/admin-login")
    target_type = str(config.get("target_type", "web") or "web").strip().lower()[:32] or "web"
    latest_scan = db.scalar(
        select(RedScanRun)
        .where(RedScanRun.site_id == site.id)
        .order_by(desc(RedScanRun.created_at))
        .limit(1)
    )
    findings = _safe_json_dict(latest_scan.findings_json) if latest_scan else {}
    missing_headers = findings.get("missing_security_headers", []) if isinstance(findings.get("missing_security_headers"), list) else []
    sensitive_paths = findings.get("sensitive_paths_open", []) if isinstance(findings.get("sensitive_paths_open"), list) else []
    matcher_words = ["login", "admin"]
    if sensitive_paths:
        first_path = sensitive_paths[0]
        if isinstance(first_path, dict) and first_path.get("path"):
            target_surface = str(first_path["path"])
    intelligence = get_latest_red_plugin_intelligence(
        db,
        site_id=site.id,
        target_surface=target_surface,
        target_type=target_type,
    )
    template_id = intelligence.get("cve_id") if intelligence and intelligence.get("cve_id") else f"brp-{site.site_code}-surface-check"
    template_id = str(template_id).lower().replace(":", "-").replace("/", "-")
    template_preview = "\n".join(
        [
            f"id: {template_id}",
            "info:",
            f"  name: {(intelligence or {}).get('title') or f'BRP {site.display_name} Surface Validation'}",
            "  severity: info",
            "  tags: brp,ai-generated,validation",
            *( [f"  reference:\n    - \"{(intelligence or {}).get('references', [''])[0]}\""] if intelligence and intelligence.get("references") else [] ),
            *( [f"  description: \"{str((intelligence or {}).get('summary_th', ''))[:180]}\""] if intelligence and intelligence.get("summary_th") else [] ),
            "http:",
            "  - method: GET",
            "    path:",
            f"      - \"{{{{BaseURL}}}}{target_surface}\"",
            "    matchers:",
            "      - type: word",
            "        words:",
            *[f"          - \"{word}\"" for word in matcher_words],
        ]
    )
    input_summary = {
        "target_surface": target_surface,
        "target_type": target_type,
        "missing_headers": len(missing_headers),
        "sensitive_paths": len(sensitive_paths),
        "has_intelligence": intelligence is not None,
    }
    output_summary = {
        "headline": f"Nuclei AI-Template Writer สำหรับ {site.site_code}",
        "severity": "medium" if sensitive_paths or missing_headers else "low",
        "summary_th": "อ่านผลสแกนล่าสุดและสร้าง YAML template สำหรับ Nuclei เพื่อให้ทีม Red/Blue นำไปใช้ตรวจสอบช่องโหว่ใหม่ได้เร็วขึ้น",
        "template_language": "yaml",
        "template_preview": template_preview,
        "rationale": [
            f"missing_security_headers={len(missing_headers)}",
            f"sensitive_paths_open={len(sensitive_paths)}",
        ],
        "source_intelligence": intelligence or {},
        "target_type": target_type,
    }
    return input_summary, output_summary


def _run_purple_incident_ghostwriter(db: Session, site: Site, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    blue_limit = max(5, min(int(config.get("blue_event_limit", 10) or 10), 100))
    latest_report = db.scalar(
        select(PurpleInsightReport)
        .where(PurpleInsightReport.site_id == site.id)
        .order_by(desc(PurpleInsightReport.created_at))
        .limit(1)
    )
    blue_rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(blue_limit)
    ).all()
    high_count = len([row for row in blue_rows if row.ai_severity == "high"])
    draft = [
        f"หัวข้อ: รายงานเหตุการณ์เบื้องต้นสำหรับไซต์ {site.display_name}",
        f"สรุปผู้บริหาร: พบเหตุการณ์ความเสี่ยงสูง {high_count} รายการในช่วงล่าสุด",
        "รายละเอียดเหตุการณ์สำคัญ:",
    ]
    for row in blue_rows[:5]:
        draft.append(
            f"- {row.event_type} จาก {row.source_ip} ระดับ {row.ai_severity} สถานะ {row.status} คำแนะนำ {row.ai_recommendation}"
        )
    if latest_report and latest_report.summary:
        draft.append(f"ข้อสังเกตจาก Purple ล่าสุด: {latest_report.summary}")
    input_summary = {"blue_event_limit": blue_limit, "has_purple_report": latest_report is not None}
    output_summary = {
        "headline": f"ร่าง Incident Report สำหรับ {site.site_code}",
        "severity": "high" if high_count > 0 else "medium",
        "summary_th": "ร่างรายงานเหตุการณ์ภาษาไทยตามข้อมูลล่าสุดของ Blue และ Purple",
        "report_th": "\n".join(draft),
    }
    return input_summary, output_summary


def _run_purple_mitre_heatmap(db: Session, site: Site, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    lookback_runs = max(1, min(int(config.get("lookback_runs", 30) or 30), 200))
    lookback_events = max(10, min(int(config.get("lookback_events", 200) or 200), 1000))
    sla_target_seconds = max(30, min(int(config.get("sla_target_seconds", 120) or 120), 3600))
    scorecard = generate_purple_executive_scorecard(
        db,
        site.id,
        lookback_runs=lookback_runs,
        lookback_events=lookback_events,
        sla_target_seconds=sla_target_seconds,
    )
    summary = scorecard.get("summary", {}) if isinstance(scorecard, dict) else {}
    heatmap = scorecard.get("heatmap", []) if isinstance(scorecard, dict) else []
    remediation = scorecard.get("remediation_sla", {}) if isinstance(scorecard, dict) else {}
    input_summary = {
        "lookback_runs": lookback_runs,
        "lookback_events": lookback_events,
        "sla_target_seconds": sla_target_seconds,
    }
    output_summary = {
        "headline": f"MITRE Heatmap สำหรับ {site.site_code}",
        "severity": "high" if remediation.get("sla_status") != "pass" else "medium",
        "summary_th": (
            f"coverage={summary.get('heatmap_coverage', 0.0)} attacked={summary.get('attacked_techniques', 0)} "
            f"covered={summary.get('covered_techniques', 0)}"
        ),
        "heatmap_top": heatmap[:6] if isinstance(heatmap, list) else [],
        "remediation_sla": remediation,
    }
    return input_summary, output_summary


PLUGIN_HANDLERS = {
    "blue_log_refiner": _run_blue_log_refiner,
    "blue_thai_alert_translator": _run_blue_thai_alert_translator,
    "blue_auto_playbook_executor": _run_blue_auto_playbook_executor,
    "red_exploit_code_generator": _run_red_exploit_code_generator,
    "red_template_writer": _run_red_template_writer,
    "purple_incident_ghostwriter": _run_purple_incident_ghostwriter,
    "purple_mitre_heatmap": _run_purple_mitre_heatmap,
}


def _merge_plugin_config(plugin: AiCoworkerPlugin, binding: SiteAiCoworkerPluginBinding | None) -> dict[str, Any]:
    config = _safe_json_dict(plugin.default_config_json)
    if binding:
        config.update(_safe_json_dict(binding.config_json))
    return config


def _maybe_route_plugin_alert(
    db: Session,
    *,
    site: Site,
    plugin: AiCoworkerPlugin,
    binding: SiteAiCoworkerPluginBinding | None,
    dry_run: bool,
    output_summary: dict[str, Any],
) -> dict[str, Any]:
    if dry_run or binding is None:
        return {"status": "skipped"}
    channels = _normalize_channels([str(item) for item in _safe_json_list(binding.notify_channels_json)])
    if not channels:
        return {"status": "skipped"}
    severity = str(output_summary.get("severity", "medium"))
    headline = str(output_summary.get("headline", plugin.display_name_th or plugin.display_name))
    summary_th = str(output_summary.get("summary_th", ""))
    return dispatch_manual_alert(
        db,
        tenant_code=site.tenant.tenant_code if site.tenant else "",
        site_code=site.site_code,
        source=f"coworker_plugin:{plugin.plugin_code}",
        severity=severity,
        title=headline,
        message=summary_th or plugin.value_statement,
        payload={
            "plugin_code": plugin.plugin_code,
            "plugin_category": plugin.category,
            "notify_channels": channels,
            "site_id": str(site.id),
            "site_code": site.site_code,
        },
    )


def run_site_coworker_plugin(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    dry_run: bool | None = None,
    force: bool = False,
    actor: str = "coworker_plugin_ai",
) -> dict[str, Any]:
    ensure_builtin_plugins(db)
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == plugin_code))
    if not plugin or not plugin.is_active:
        return {"status": "plugin_not_found", "plugin_code": plugin_code}
    binding = db.scalar(
        select(SiteAiCoworkerPluginBinding).where(
            SiteAiCoworkerPluginBinding.site_id == site.id,
            SiteAiCoworkerPluginBinding.plugin_id == plugin.id,
        )
    )

    if binding and not binding.enabled and not force:
        return {
            "status": "disabled",
            "site_id": str(site.id),
            "plugin_code": plugin.plugin_code,
            "binding": _binding_row(binding),
        }

    handler = PLUGIN_HANDLERS.get(plugin.plugin_code)
    if handler is None:
        return {"status": "handler_not_found", "plugin_code": plugin.plugin_code}

    resolved_dry_run = True if dry_run is None else bool(dry_run)
    config = _merge_plugin_config(plugin, binding)
    input_summary, output_summary = handler(db, site, config)
    alert = _maybe_route_plugin_alert(
        db,
        site=site,
        plugin=plugin,
        binding=binding,
        dry_run=resolved_dry_run,
        output_summary=output_summary,
    )

    run = AiCoworkerPluginRun(
        plugin_id=plugin.id,
        site_id=site.id,
        status="dry_run" if resolved_dry_run else "ok",
        dry_run=resolved_dry_run,
        input_summary_json=_as_json(
            {
                "actor": actor,
                "force": force,
                **input_summary,
            }
        ),
        output_summary_json=_as_json(output_summary),
        alert_routed=alert.get("status") == "ok",
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return {
        "status": run.status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "plugin": _plugin_catalog_row(plugin),
        "binding": _binding_row(binding) if binding else None,
        "run": _run_row(run),
        "alert": alert,
    }


def list_site_coworker_plugin_runs(
    db: Session,
    *,
    site_id: UUID,
    category: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    ensure_builtin_plugins(db)
    site = db.get(Site, site_id)
    if not site:
        return {"count": 0, "rows": []}

    rows = db.scalars(
        select(AiCoworkerPluginRun)
        .where(AiCoworkerPluginRun.site_id == site.id)
        .order_by(desc(AiCoworkerPluginRun.created_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    normalized_category = _normalize_category(category)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        plugin = db.get(AiCoworkerPlugin, row.plugin_id)
        if not plugin:
            continue
        if normalized_category and plugin.category != normalized_category:
            continue
        filtered.append(
            {
                **_run_row(row),
                "plugin_code": plugin.plugin_code,
                "display_name": plugin.display_name,
                "display_name_th": plugin.display_name_th,
                "category": plugin.category,
            }
        )
    return {"site_id": str(site.id), "count": len(filtered), "rows": filtered}


def _is_binding_due(binding: SiteAiCoworkerPluginBinding, last_run: AiCoworkerPluginRun | None, now: datetime) -> bool:
    if not bool(binding.enabled) or not bool(binding.auto_run):
        return False
    if last_run is None or last_run.created_at is None:
        return True
    created_at = last_run.created_at if last_run.created_at.tzinfo else last_run.created_at.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(minutes=max(5, int(binding.schedule_interval_minutes or 60)))
    return created_at <= cutoff


def run_coworker_plugin_scheduler(
    db: Session,
    *,
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "coworker_plugin_ai",
) -> dict[str, Any]:
    ensure_builtin_plugins(db)
    bindings = db.scalars(
        select(SiteAiCoworkerPluginBinding)
        .where(
            SiteAiCoworkerPluginBinding.enabled.is_(True),
            SiteAiCoworkerPluginBinding.auto_run.is_(True),
        )
        .order_by(desc(SiteAiCoworkerPluginBinding.updated_at))
        .limit(max(1, min(limit, 2000)))
    ).all()
    now = datetime.now(timezone.utc)
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for binding in bindings:
        plugin = db.get(AiCoworkerPlugin, binding.plugin_id)
        site = db.get(Site, binding.site_id)
        if not plugin or not site:
            skipped.append({"binding_id": str(binding.id), "reason": "plugin_or_site_not_found"})
            continue
        last_run = db.scalar(
            select(AiCoworkerPluginRun)
            .where(
                AiCoworkerPluginRun.plugin_id == plugin.id,
                AiCoworkerPluginRun.site_id == site.id,
            )
            .order_by(desc(AiCoworkerPluginRun.created_at))
            .limit(1)
        )
        if not _is_binding_due(binding, last_run, now):
            skipped.append({"site_id": str(site.id), "plugin_code": plugin.plugin_code, "reason": "schedule_not_due"})
            continue
        result = run_site_coworker_plugin(
            db,
            site_id=site.id,
            plugin_code=plugin.plugin_code,
            dry_run=dry_run_override,
            force=False,
            actor=actor,
        )
        executed.append(
            {
                "site_id": str(site.id),
                "site_code": site.site_code,
                "plugin_code": plugin.plugin_code,
                "status": str(result.get("status", "unknown")),
                "run_id": str((result.get("run", {}) or {}).get("run_id", "")),
            }
        )
    return {
        "timestamp": now.isoformat(),
        "scheduled_binding_count": len(bindings),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def process_coworker_plugin_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_coworker_plugin_scheduler(
            db,
            limit=limit,
            dry_run_override=None,
            actor="coworker_plugin_ai",
        )
