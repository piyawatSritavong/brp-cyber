from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.services import purple_plugin_exports


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, *, scalar_values=None, scalar_batches=None, object_map=None):
        self.scalar_values = list(scalar_values or [])
        self.scalar_batches = list(scalar_batches or [])
        self.object_map = object_map or {}
        self.added = []

    def get(self, _model, object_id):
        return self.object_map.get(object_id)

    def scalar(self, _stmt):
        if not self.scalar_values:
            return None
        return self.scalar_values.pop(0)

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else list(self.added)
        return _FakeScalarResult(rows)

    def add(self, row):
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        self.added.append(row)
        self.object_map[row.id] = row

    def commit(self):
        return None

    def refresh(self, row):
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        self.object_map[row.id] = row
        return None


def test_list_purple_export_template_packs_filters_by_kind() -> None:
    result = purple_plugin_exports.list_purple_export_template_packs(kind="incident_report")
    assert result["status"] == "ok"
    assert result["count"] >= 2
    assert all(row["kind"] == "incident_report" for row in result["rows"])


def test_export_purple_mitre_heatmap_returns_attack_layer_json(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    db = _FakeDB(object_map={site_id: site})

    monkeypatch.setattr(
        purple_plugin_exports,
        "generate_purple_executive_scorecard",
        lambda _db, _site_id, **_kwargs: {
            "summary": {
                "attacked_techniques": 2,
                "covered_techniques": 1,
                "heatmap_coverage": 0.5,
            },
            "remediation_sla": {"sla_status": "at_risk", "estimated_mttr_seconds": 180},
            "heatmap": [
                {
                    "technique_id": "T1110",
                    "detection_status": "covered",
                    "attack_count": 3,
                    "mitigation_time_seconds": 60,
                    "sla_status": "pass",
                    "recommendation": "tighten velocity rule",
                }
            ],
        },
    )

    result = purple_plugin_exports.export_purple_mitre_heatmap(
        db,
        site_id=site_id,
        export_format="attack_layer_json",
    )

    assert result["status"] == "ok"
    assert result["export"]["export_format"] == "attack_layer_json"
    assert "\"techniqueID\": \"T1110\"" in result["export"]["content"]


def test_export_purple_incident_report_returns_sections() -> None:
    site_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    latest_report = SimpleNamespace(summary="Purple summary", created_at=now)
    blue_rows = [
        SimpleNamespace(
            created_at=now,
            ai_severity="high",
            event_type="waf_http",
            source_ip="203.0.113.10",
            ai_recommendation="block_ip",
            status="applied",
            action_taken="block_ip",
        )
    ]
    db = _FakeDB(object_map={site_id: site}, scalar_values=[latest_report], scalar_batches=[blue_rows])

    result = purple_plugin_exports.export_purple_incident_report(
        db,
        site_id=site_id,
        template_pack="incident_nca_th",
        export_format="markdown",
    )

    assert result["status"] == "ok"
    assert result["export"]["template_pack"]["pack_code"] == "incident_nca_th"
    assert len(result["export"]["sections"]) >= 3
    assert "Purple summary" in result["export"]["content"]


def test_export_purple_incident_report_returns_native_pdf() -> None:
    site_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    latest_report = SimpleNamespace(summary="Purple summary", created_at=now)
    blue_rows = [
        SimpleNamespace(
            created_at=now,
            ai_severity="high",
            event_type="waf_http",
            source_ip="203.0.113.10",
            ai_recommendation="block_ip",
            status="applied",
            action_taken="block_ip",
        )
    ]
    db = _FakeDB(object_map={site_id: site}, scalar_values=[latest_report], scalar_batches=[blue_rows])

    result = purple_plugin_exports.export_purple_incident_report(
        db,
        site_id=site_id,
        template_pack="incident_company_standard",
        export_format="pdf",
    )

    assert result["status"] == "ok"
    assert result["export"]["export_format"] == "pdf"
    assert result["export"]["renderer"] == "native_binary"
    assert result["export"]["mime_type"] == "application/pdf"
    assert result["export"]["content_base64"]
    assert result["export"]["byte_size"] > 20


def test_export_purple_regulated_report_includes_iso_and_nist(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    latest_report = SimpleNamespace(summary="Compliance summary")
    blue_rows = [
        SimpleNamespace(
            event_type="auth_login",
            ai_severity="medium",
            source_ip="198.51.100.44",
            ai_recommendation="limit_user",
        )
    ]
    db = _FakeDB(object_map={site_id: site}, scalar_values=[latest_report], scalar_batches=[blue_rows])

    monkeypatch.setattr(
        purple_plugin_exports,
        "generate_iso27001_gap_template",
        lambda _db, _site_id, limit=200: {
            "controls": [{"control_id": "A.5.1", "status": "partial", "control_name": "Policies"}]
        },
    )
    monkeypatch.setattr(
        purple_plugin_exports,
        "generate_nist_csf_gap_template",
        lambda _db, _site_id, limit=200: {
            "controls": [{"control_id": "ID.RA-01", "status": "implemented", "control_name": "Asset risk"}]
        },
    )

    result = purple_plugin_exports.export_purple_regulated_report(
        db,
        site_id=site_id,
        template_pack="regulated_iso27001_audit",
        export_format="json",
    )

    assert result["status"] == "ok"
    assert result["export"]["template_pack"]["pack_code"] == "regulated_iso27001_audit"
    sections = result["export"]["sections"]
    assert any(section["section"] == "ISO 27001 Gap Snapshot" for section in sections)
    assert any(section["section"] == "NIST CSF Gap Snapshot" for section in sections)


def test_export_purple_regulated_report_returns_native_docx(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    latest_report = SimpleNamespace(summary="Compliance summary")
    blue_rows = [
        SimpleNamespace(
            event_type="auth_login",
            ai_severity="medium",
            source_ip="198.51.100.44",
            ai_recommendation="limit_user",
        )
    ]
    db = _FakeDB(object_map={site_id: site}, scalar_values=[latest_report], scalar_batches=[blue_rows])

    monkeypatch.setattr(
        purple_plugin_exports,
        "generate_iso27001_gap_template",
        lambda _db, _site_id, limit=200: {
            "controls": [{"control_id": "A.5.1", "status": "partial", "control_name": "Policies"}]
        },
    )
    monkeypatch.setattr(
        purple_plugin_exports,
        "generate_nist_csf_gap_template",
        lambda _db, _site_id, limit=200: {
            "controls": [{"control_id": "ID.RA-01", "status": "implemented", "control_name": "Asset risk"}]
        },
    )

    result = purple_plugin_exports.export_purple_regulated_report(
        db,
        site_id=site_id,
        template_pack="regulated_nca_th",
        export_format="docx",
    )

    assert result["status"] == "ok"
    assert result["export"]["export_format"] == "docx"
    assert result["export"]["renderer"] == "native_binary"
    assert result["export"]["mime_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert result["export"]["content_base64"]
    assert result["export"]["byte_size"] > 20


def test_request_review_and_list_purple_report_releases() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    db = _FakeDB(object_map={site_id: site})

    requested = purple_plugin_exports.request_purple_report_release(
        db,
        site_id=site_id,
        report_kind="incident_report",
        export_format="pdf",
        title="Incident Final",
        filename="incident-final.pdf",
        payload={"renderer": "native_binary", "byte_size": 128},
        requester="purple_service_operator",
        note="requested_from_test",
    )

    assert requested["status"] == "ok"
    release_id = requested["release"]["release_id"]

    reviewed = purple_plugin_exports.review_purple_report_release(
        db,
        release_id=UUID(release_id),
        approve=True,
        approver="security_lead",
        note="approved_in_test",
    )

    assert reviewed["status"] == "approved"
    assert reviewed["release"]["approved_by"] == "security_lead"

    listed = purple_plugin_exports.list_purple_report_releases(db, site_id=site_id, limit=10)
    assert listed["status"] == "ok"
    assert listed["count"] == 1
    assert listed["rows"][0]["status"] == "approved"
