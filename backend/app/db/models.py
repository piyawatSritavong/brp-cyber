from __future__ import annotations

import enum
import json
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RoleName(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"
    service = "service"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    users: Mapped[list[User]] = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    api_keys: Mapped[list[TenantApiKey]] = relationship("TenantApiKey", back_populates="tenant", cascade="all, delete-orphan")
    sites: Mapped[list[Site]] = relationship("Site", back_populates="tenant", cascade="all, delete-orphan")
    playbook_policies: Mapped[list[TenantPlaybookPolicy]] = relationship(
        "TenantPlaybookPolicy",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    action_center_policies: Mapped[list[ActionCenterRoutingPolicy]] = relationship(
        "ActionCenterRoutingPolicy",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    connector_sla_profiles: Mapped[list[ConnectorSlaProfile]] = relationship(
        "ConnectorSlaProfile",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    connector_sla_breaches: Mapped[list[ConnectorSlaBreachEvent]] = relationship(
        "ConnectorSlaBreachEvent",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    action_center_events: Mapped[list[ActionCenterDispatchEvent]] = relationship(
        "ActionCenterDispatchEvent",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    connector_delivery_events: Mapped[list[ConnectorDeliveryEvent]] = relationship(
        "ConnectorDeliveryEvent",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    connector_credentials: Mapped[list[ConnectorCredentialVault]] = relationship(
        "ConnectorCredentialVault",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    connector_credential_rotation_events: Mapped[list[ConnectorCredentialRotationEvent]] = relationship(
        "ConnectorCredentialRotationEvent",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    credential_hygiene_policies: Mapped[list[ConnectorCredentialHygienePolicy]] = relationship(
        "ConnectorCredentialHygienePolicy",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    credential_hygiene_runs: Mapped[list[ConnectorCredentialHygieneRun]] = relationship(
        "ConnectorCredentialHygieneRun",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    connector_reliability_policies: Mapped[list[ConnectorReliabilityPolicy]] = relationship(
        "ConnectorReliabilityPolicy",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    connector_reliability_runs: Mapped[list[ConnectorReliabilityRun]] = relationship(
        "ConnectorReliabilityRun",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="users")
    roles: Mapped[list[UserRole]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_email_per_tenant"),)


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[RoleName] = mapped_column(Enum(RoleName, name="role_name"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="roles")

    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_role"),)


class TenantApiKey(Base):
    __tablename__ = "tenant_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    key_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="api_keys")


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    site_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    base_url: Mapped[str] = mapped_column(String(2048), unique=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="sites")
    red_scans: Mapped[list[RedScanRun]] = relationship("RedScanRun", back_populates="site", cascade="all, delete-orphan")
    blue_events: Mapped[list[BlueEventLog]] = relationship("BlueEventLog", back_populates="site", cascade="all, delete-orphan")
    purple_reports: Mapped[list[PurpleInsightReport]] = relationship(
        "PurpleInsightReport",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    integration_events: Mapped[list[IntegrationEvent]] = relationship(
        "IntegrationEvent",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_exploit_paths: Mapped[list[RedExploitPathRun]] = relationship(
        "RedExploitPathRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_exploit_autopilot_policies: Mapped[list[RedExploitAutopilotPolicy]] = relationship(
        "RedExploitAutopilotPolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_exploit_autopilot_runs: Mapped[list[RedExploitAutopilotRun]] = relationship(
        "RedExploitAutopilotRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    blue_detection_rules: Mapped[list[BlueDetectionRule]] = relationship(
        "BlueDetectionRule",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    blue_detection_tuning_runs: Mapped[list[BlueDetectionTuningRun]] = relationship(
        "BlueDetectionTuningRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    blue_detection_autotune_policies: Mapped[list[BlueDetectionAutotunePolicy]] = relationship(
        "BlueDetectionAutotunePolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    blue_detection_autotune_runs: Mapped[list[BlueDetectionAutotuneRun]] = relationship(
        "BlueDetectionAutotuneRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    phase_objective_checks: Mapped[list[PhaseObjectiveCheck]] = relationship(
        "PhaseObjectiveCheck",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    soar_playbook_executions: Mapped[list[SoarPlaybookExecution]] = relationship(
        "SoarPlaybookExecution",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    connector_delivery_events: Mapped[list[ConnectorDeliveryEvent]] = relationship(
        "ConnectorDeliveryEvent",
        back_populates="site",
        cascade="all, delete-orphan",
    )

    def config(self) -> dict[str, object]:
        try:
            return json.loads(self.config_json or "{}")
        except Exception:
            return {}


class RedScanRun(Base):
    __tablename__ = "red_scan_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    scan_type: Mapped[str] = mapped_column(String(64), default="baseline_scan")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    findings_json: Mapped[str] = mapped_column(Text, default="{}")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_scans")


class BlueEventLog(Base):
    __tablename__ = "blue_event_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="http_event")
    source_ip: Mapped[str] = mapped_column(String(64), default="unknown")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    ai_severity: Mapped[str] = mapped_column(String(16), default="low")
    ai_recommendation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    action_taken: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_events")


class PurpleInsightReport(Base):
    __tablename__ = "purple_insight_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    ai_analysis_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="purple_reports")


class IntegrationEvent(Base):
    __tablename__ = "integration_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    event_kind: Mapped[str] = mapped_column(String(64), default="security_finding")
    raw_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    normalized_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site | None] = relationship("Site", back_populates="integration_events")


class ThreatContentPack(Base):
    __tablename__ = "threat_content_packs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pack_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), default="generic")
    mitre_techniques_json: Mapped[str] = mapped_column(Text, default="[]")
    attack_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    validation_mode: Mapped[str] = mapped_column(String(32), default="simulation_safe")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    exploit_path_runs: Mapped[list[RedExploitPathRun]] = relationship(
        "RedExploitPathRun",
        back_populates="threat_pack",
    )


class ThreatContentPipelinePolicy(Base):
    __tablename__ = "threat_content_pipeline_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(64), default="global", unique=True, index=True)
    min_refresh_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    preferred_categories_json: Mapped[str] = mapped_column(Text, default="[]")
    max_packs_per_run: Mapped[int] = mapped_column(Integer, default=8)
    auto_activate: Mapped[bool] = mapped_column(Boolean, default=True)
    route_alert: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ThreatContentPipelineRun(Base):
    __tablename__ = "threat_content_pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(64), default="global", index=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    selected_categories_json: Mapped[str] = mapped_column(Text, default="[]")
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    refreshed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    activated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    alert_routed: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RedExploitPathRun(Base):
    __tablename__ = "red_exploit_path_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    threat_pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("threat_content_packs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="completed")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    path_graph_json: Mapped[str] = mapped_column(Text, default="{}")
    proof_json: Mapped[str] = mapped_column(Text, default="{}")
    safe_mode_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_exploit_paths")
    threat_pack: Mapped[ThreatContentPack | None] = relationship("ThreatContentPack", back_populates="exploit_path_runs")
    detection_tuning_runs: Mapped[list[BlueDetectionTuningRun]] = relationship(
        "BlueDetectionTuningRun",
        back_populates="exploit_path_run",
    )
    autopilot_runs: Mapped[list[RedExploitAutopilotRun]] = relationship(
        "RedExploitAutopilotRun",
        back_populates="exploit_path_run",
    )


class RedExploitAutopilotPolicy(Base):
    __tablename__ = "red_exploit_autopilot_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    min_risk_score: Mapped[int] = mapped_column(Integer, default=50)
    min_risk_tier: Mapped[str] = mapped_column(String(16), default="medium")
    preferred_pack_category: Mapped[str] = mapped_column(String(64), default="identity")
    target_surface: Mapped[str] = mapped_column(String(1024), default="/admin-login")
    simulation_depth: Mapped[int] = mapped_column(Integer, default=3)
    max_requests_per_minute: Mapped[int] = mapped_column(Integer, default=30)
    stop_on_critical: Mapped[bool] = mapped_column(Boolean, default=True)
    simulation_only: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_run: Mapped[bool] = mapped_column(Boolean, default=False)
    route_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=120)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_exploit_autopilot_policies")

    __table_args__ = (UniqueConstraint("site_id", name="uq_red_exploit_autopilot_policy"),)


class RedExploitAutopilotRun(Base):
    __tablename__ = "red_exploit_autopilot_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    exploit_path_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("red_exploit_path_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="ok")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")
    threat_pack_code: Mapped[str] = mapped_column(String(80), default="")
    path_node_count: Mapped[int] = mapped_column(Integer, default=0)
    path_edge_count: Mapped[int] = mapped_column(Integer, default=0)
    proof_confidence: Mapped[str] = mapped_column(String(16), default="low")
    should_run: Mapped[bool] = mapped_column(Boolean, default=False)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_routed: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_exploit_autopilot_runs")
    exploit_path_run: Mapped[RedExploitPathRun | None] = relationship("RedExploitPathRun", back_populates="autopilot_runs")


class BlueDetectionRule(Base):
    __tablename__ = "blue_detection_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    rule_name: Mapped[str] = mapped_column(String(255))
    rule_logic_json: Mapped[str] = mapped_column(Text, default="{}")
    source: Mapped[str] = mapped_column(String(64), default="ai_copilot")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_detection_rules")


class BlueDetectionTuningRun(Base):
    __tablename__ = "blue_detection_tuning_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    exploit_path_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("red_exploit_path_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="completed")
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]")
    before_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    after_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_detection_tuning_runs")
    exploit_path_run: Mapped[RedExploitPathRun | None] = relationship("RedExploitPathRun", back_populates="detection_tuning_runs")


class BlueDetectionAutotunePolicy(Base):
    __tablename__ = "blue_detection_autotune_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    min_risk_score: Mapped[int] = mapped_column(Integer, default=60)
    min_risk_tier: Mapped[str] = mapped_column(String(16), default="high")
    target_detection_coverage_pct: Mapped[int] = mapped_column(Integer, default=90)
    max_rules_per_run: Mapped[int] = mapped_column(Integer, default=3)
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    route_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_detection_autotune_policies")

    __table_args__ = (UniqueConstraint("site_id", name="uq_blue_detection_autotune_policy"),)


class BlueDetectionAutotuneRun(Base):
    __tablename__ = "blue_detection_autotune_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")
    coverage_before_pct: Mapped[int] = mapped_column(Integer, default=0)
    coverage_after_pct: Mapped[int] = mapped_column(Integer, default=0)
    recommendation_count: Mapped[int] = mapped_column(Integer, default=0)
    applied_count: Mapped[int] = mapped_column(Integer, default=0)
    alert_routed: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_detection_autotune_runs")


class PhaseObjectiveCheck(Base):
    __tablename__ = "phase_objective_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    phase_code: Mapped[str] = mapped_column(String(32), index=True)
    phase_title: Mapped[str] = mapped_column(String(255), default="")
    objective_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    deliverables_json: Mapped[str] = mapped_column(Text, default="[]")
    scope_status: Mapped[str] = mapped_column(String(16), default="in_scope")
    scope_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site | None] = relationship("Site", back_populates="phase_objective_checks")


class SoarPlaybook(Base):
    __tablename__ = "soar_playbooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), default="response")
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    scope: Mapped[str] = mapped_column(String(32), default="community")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    action_policy_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    executions: Mapped[list[SoarPlaybookExecution]] = relationship(
        "SoarPlaybookExecution",
        back_populates="playbook",
    )


class SoarPlaybookExecution(Base):
    __tablename__ = "soar_playbook_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    playbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("soar_playbooks.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending_approval")
    requested_by: Mapped[str] = mapped_column(String(128), default="ai_agent")
    approved_by: Mapped[str] = mapped_column(String(128), default="")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    run_params_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="soar_playbook_executions")
    playbook: Mapped[SoarPlaybook] = relationship("SoarPlaybook", back_populates="executions")


class ConnectorDeliveryEvent(Base):
    __tablename__ = "connector_delivery_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    connector_source: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(32), default="delivery_attempt")
    status: Mapped[str] = mapped_column(String(32), default="success")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site | None] = relationship("Site", back_populates="connector_delivery_events")
    tenant: Mapped[Tenant | None] = relationship("Tenant", back_populates="connector_delivery_events")


class TenantPlaybookPolicy(Base):
    __tablename__ = "tenant_playbook_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    policy_version: Mapped[str] = mapped_column(String(16), default="1.0")
    owner: Mapped[str] = mapped_column(String(64), default="security")
    require_approval_by_scope_json: Mapped[str] = mapped_column(Text, default="{}")
    require_approval_by_category_json: Mapped[str] = mapped_column(Text, default="{}")
    delegated_approvers_json: Mapped[str] = mapped_column(Text, default="[]")
    blocked_playbook_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    allow_partner_scope: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_approve_dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="playbook_policies")

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_playbook_policy"),)


class ActionCenterRoutingPolicy(Base):
    __tablename__ = "action_center_routing_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    policy_version: Mapped[str] = mapped_column(String(16), default="1.0")
    owner: Mapped[str] = mapped_column(String(64), default="security")
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    line_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    min_severity: Mapped[str] = mapped_column(String(16), default="high")
    routing_tags_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="action_center_policies")

    __table_args__ = (UniqueConstraint("tenant_id", name="uq_action_center_policy"),)


class ActionCenterDispatchEvent(Base):
    __tablename__ = "action_center_dispatch_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    title: Mapped[str] = mapped_column(String(255), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    telegram_status: Mapped[str] = mapped_column(String(16), default="skipped")
    line_status: Mapped[str] = mapped_column(String(16), default="skipped")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="action_center_events")


class ConnectorSlaProfile(Base):
    __tablename__ = "connector_sla_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="*")
    min_events: Mapped[int] = mapped_column(Integer, default=20)
    min_success_rate: Mapped[int] = mapped_column(Integer, default=95)
    max_dead_letter_count: Mapped[int] = mapped_column(Integer, default=5)
    max_average_latency_ms: Mapped[int] = mapped_column(Integer, default=5000)
    notify_on_breach: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="connector_sla_profiles")

    __table_args__ = (UniqueConstraint("tenant_id", "connector_source", name="uq_connector_sla_profile"),)


class ConnectorSlaBreachEvent(Base):
    __tablename__ = "connector_sla_breach_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    connector_source: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="high")
    breach_reason: Mapped[str] = mapped_column(Text, default="")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    routed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="connector_sla_breaches")


class ConnectorCredentialVault(Base):
    __tablename__ = "connector_credential_vaults"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), index=True)
    credential_name: Mapped[str] = mapped_column(String(64), index=True)
    secret_ciphertext: Mapped[str] = mapped_column(Text, default="")
    secret_fingerprint: Mapped[str] = mapped_column(String(64), default="")
    secret_version: Mapped[int] = mapped_column(Integer, default=1)
    external_ref: Mapped[str] = mapped_column(String(255), default="")
    rotation_interval_days: Mapped[int] = mapped_column(Integer, default=30)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="connector_credentials")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connector_source",
            "credential_name",
            name="uq_connector_credential_vault",
        ),
    )


class ConnectorCredentialRotationEvent(Base):
    __tablename__ = "connector_credential_rotation_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), index=True)
    credential_name: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    rotation_reason: Mapped[str] = mapped_column(String(255), default="scheduled_rotation")
    old_version: Mapped[int] = mapped_column(Integer, default=0)
    new_version: Mapped[int] = mapped_column(Integer, default=1)
    prev_signature: Mapped[str] = mapped_column(String(128), default="")
    signature: Mapped[str] = mapped_column(String(128), default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="connector_credential_rotation_events")


class ConnectorCredentialHygienePolicy(Base):
    __tablename__ = "connector_credential_hygiene_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="*")
    warning_days: Mapped[int] = mapped_column(Integer, default=7)
    max_rotate_per_run: Mapped[int] = mapped_column(Integer, default=20)
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    route_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="credential_hygiene_policies")

    __table_args__ = (UniqueConstraint("tenant_id", "connector_source", name="uq_credential_hygiene_policy"),)


class ConnectorCredentialHygieneRun(Base):
    __tablename__ = "connector_credential_hygiene_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="*")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    selected_count: Mapped[int] = mapped_column(Integer, default=0)
    planned_count: Mapped[int] = mapped_column(Integer, default=0)
    executed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")
    alert_routed: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="credential_hygiene_runs")


class ConnectorReliabilityPolicy(Base):
    __tablename__ = "connector_reliability_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="*")
    max_replay_per_run: Mapped[int] = mapped_column(Integer, default=25)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    auto_replay_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    route_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="connector_reliability_policies")

    __table_args__ = (UniqueConstraint("tenant_id", "connector_source", name="uq_connector_reliability_policy"),)


class ConnectorReliabilityRun(Base):
    __tablename__ = "connector_reliability_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="*")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    backlog_count: Mapped[int] = mapped_column(Integer, default=0)
    selected_count: Mapped[int] = mapped_column(Integer, default=0)
    replayed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")
    alert_routed: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="connector_reliability_runs")
