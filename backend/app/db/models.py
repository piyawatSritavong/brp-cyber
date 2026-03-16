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
    red_shadow_pentest_policies: Mapped[list[RedShadowPentestPolicy]] = relationship(
        "RedShadowPentestPolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_shadow_pentest_runs: Mapped[list[RedShadowPentestRun]] = relationship(
        "RedShadowPentestRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_social_engineering_runs: Mapped[list[RedSocialEngineeringRun]] = relationship(
        "RedSocialEngineeringRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_social_roster_entries: Mapped[list[RedSocialRosterEntry]] = relationship(
        "RedSocialRosterEntry",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_social_campaign_policies: Mapped[list[RedSocialCampaignPolicy]] = relationship(
        "RedSocialCampaignPolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_social_campaign_executions: Mapped[list[RedSocialCampaignExecution]] = relationship(
        "RedSocialCampaignExecution",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_social_campaign_recipients: Mapped[list[RedSocialCampaignRecipient]] = relationship(
        "RedSocialCampaignRecipient",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_vulnerability_findings: Mapped[list[RedVulnerabilityFinding]] = relationship(
        "RedVulnerabilityFinding",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_vulnerability_validation_runs: Mapped[list[RedVulnerabilityValidationRun]] = relationship(
        "RedVulnerabilityValidationRun",
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
    blue_threat_localizer_runs: Mapped[list[BlueThreatLocalizerRun]] = relationship(
        "BlueThreatLocalizerRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    blue_threat_localizer_policies: Mapped[list[BlueThreatLocalizerPolicy]] = relationship(
        "BlueThreatLocalizerPolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    blue_managed_responder_policies: Mapped[list[BlueManagedResponderPolicy]] = relationship(
        "BlueManagedResponderPolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    blue_managed_responder_runs: Mapped[list[BlueManagedResponderRun]] = relationship(
        "BlueManagedResponderRun",
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
    coworker_plugin_bindings: Mapped[list[SiteAiCoworkerPluginBinding]] = relationship(
        "SiteAiCoworkerPluginBinding",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    coworker_plugin_runs: Mapped[list[AiCoworkerPluginRun]] = relationship(
        "AiCoworkerPluginRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_plugin_intelligence_items: Mapped[list[RedPluginIntelligenceItem]] = relationship(
        "RedPluginIntelligenceItem",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_plugin_safety_policies: Mapped[list[RedPluginSafetyPolicy]] = relationship(
        "RedPluginSafetyPolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_plugin_intelligence_sync_sources: Mapped[list[RedPluginIntelligenceSyncSource]] = relationship(
        "RedPluginIntelligenceSyncSource",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    red_plugin_intelligence_sync_runs: Mapped[list[RedPluginIntelligenceSyncRun]] = relationship(
        "RedPluginIntelligenceSyncRun",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    embedded_workflow_endpoints: Mapped[list[SiteEmbeddedWorkflowEndpoint]] = relationship(
        "SiteEmbeddedWorkflowEndpoint",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    embedded_workflow_invocations: Mapped[list[SiteEmbeddedWorkflowInvocation]] = relationship(
        "SiteEmbeddedWorkflowInvocation",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    coworker_delivery_profiles: Mapped[list[SiteAiCoworkerDeliveryProfile]] = relationship(
        "SiteAiCoworkerDeliveryProfile",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    coworker_delivery_escalation_policies: Mapped[list[SiteAiCoworkerDeliveryEscalationPolicy]] = relationship(
        "SiteAiCoworkerDeliveryEscalationPolicy",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    coworker_delivery_events: Mapped[list[AiCoworkerDeliveryEvent]] = relationship(
        "AiCoworkerDeliveryEvent",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    purple_roi_dashboard_snapshots: Mapped[list[PurpleRoiDashboardSnapshot]] = relationship(
        "PurpleRoiDashboardSnapshot",
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


class AiCoworkerPlugin(Base):
    __tablename__ = "ai_coworker_plugins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    display_name_th: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(32), default="blue")
    plugin_kind: Mapped[str] = mapped_column(String(64), default="analysis")
    execution_mode: Mapped[str] = mapped_column(String(32), default="manual")
    description: Mapped[str] = mapped_column(Text, default="")
    value_statement: Mapped[str] = mapped_column(Text, default="")
    default_config_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    bindings: Mapped[list[SiteAiCoworkerPluginBinding]] = relationship(
        "SiteAiCoworkerPluginBinding",
        back_populates="plugin",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list[AiCoworkerPluginRun]] = relationship(
        "AiCoworkerPluginRun",
        back_populates="plugin",
        cascade="all, delete-orphan",
    )


class SiteAiCoworkerPluginBinding(Base):
    __tablename__ = "site_ai_coworker_plugin_bindings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    plugin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_coworker_plugins.id", ondelete="CASCADE"),
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_run: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    notify_channels_json: Mapped[str] = mapped_column(Text, default="[]")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="coworker_plugin_bindings")
    plugin: Mapped[AiCoworkerPlugin] = relationship("AiCoworkerPlugin", back_populates="bindings")

    __table_args__ = (UniqueConstraint("site_id", "plugin_id", name="uq_site_ai_coworker_plugin_binding"),)


class AiCoworkerPluginRun(Base):
    __tablename__ = "ai_coworker_plugin_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_coworker_plugins.id", ondelete="CASCADE"),
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    input_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    output_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    alert_routed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    plugin: Mapped[AiCoworkerPlugin] = relationship("AiCoworkerPlugin", back_populates="runs")
    site: Mapped[Site] = relationship("Site", back_populates="coworker_plugin_runs")


class RedPluginIntelligenceItem(Base):
    __tablename__ = "red_plugin_intelligence_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="article", index=True)
    source_name: Mapped[str] = mapped_column(String(64), default="manual", index=True)
    source_item_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    summary_th: Mapped[str] = mapped_column(Text, default="")
    cve_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    target_surface: Mapped[str] = mapped_column(String(512), default="")
    target_type: Mapped[str] = mapped_column(String(32), default="web", index=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    references_json: Mapped[str] = mapped_column(Text, default="[]")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_plugin_intelligence_items")

    __table_args__ = (UniqueConstraint("site_id", "source_name", "source_item_id", name="uq_red_plugin_intel_source"),)


class RedPluginSafetyPolicy(Base):
    __tablename__ = "red_plugin_safety_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), default="web")
    max_http_requests_per_run: Mapped[int] = mapped_column(Integer, default=5)
    max_script_lines: Mapped[int] = mapped_column(Integer, default=80)
    allow_network_calls: Mapped[bool] = mapped_column(Boolean, default=True)
    require_comment_header: Mapped[bool] = mapped_column(Boolean, default=True)
    require_disclaimer: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_modules_json: Mapped[str] = mapped_column(Text, default='["requests"]')
    blocked_modules_json: Mapped[str] = mapped_column(Text, default='["subprocess","socket","paramiko"]')
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_plugin_safety_policies")

    __table_args__ = (UniqueConstraint("site_id", "target_type", name="uq_red_plugin_safety_policy"),)


class RedPluginIntelligenceSyncSource(Base):
    __tablename__ = "red_plugin_intelligence_sync_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    source_name: Mapped[str] = mapped_column(String(64), default="external_feed", index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="article")
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    target_type: Mapped[str] = mapped_column(String(32), default="web")
    parser_kind: Mapped[str] = mapped_column(String(32), default="json_feed")
    request_headers_json: Mapped[str] = mapped_column(Text, default="{}")
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_plugin_intelligence_sync_sources")
    runs: Mapped[list[RedPluginIntelligenceSyncRun]] = relationship(
        "RedPluginIntelligenceSyncRun",
        back_populates="sync_source",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("site_id", "source_name", "source_url", name="uq_red_plugin_intel_sync_source"),)


class RedPluginIntelligenceSyncRun(Base):
    __tablename__ = "red_plugin_intelligence_sync_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    sync_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("red_plugin_intelligence_sync_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="ok")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    actor: Mapped[str] = mapped_column(String(128), default="red_plugin_sync_ai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_plugin_intelligence_sync_runs")
    sync_source: Mapped[RedPluginIntelligenceSyncSource | None] = relationship(
        "RedPluginIntelligenceSyncSource",
        back_populates="runs",
    )


class SiteEmbeddedWorkflowEndpoint(Base):
    __tablename__ = "site_embedded_workflow_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    endpoint_code: Mapped[str] = mapped_column(String(80), index=True)
    workflow_type: Mapped[str] = mapped_column(String(32), default="coworker_plugin")
    plugin_code: Mapped[str] = mapped_column(String(80), default="")
    connector_source: Mapped[str] = mapped_column(String(64), default="generic")
    default_event_kind: Mapped[str] = mapped_column(String(64), default="security_event")
    secret_hash: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    dry_run_default: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="embedded_workflow_endpoints")
    invocations: Mapped[list[SiteEmbeddedWorkflowInvocation]] = relationship(
        "SiteEmbeddedWorkflowInvocation",
        back_populates="endpoint",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("site_id", "endpoint_code", name="uq_site_embedded_workflow_endpoint"),)


class SiteEmbeddedWorkflowInvocation(Base):
    __tablename__ = "site_embedded_workflow_invocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("site_embedded_workflow_endpoints.id", ondelete="CASCADE"),
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    endpoint_code: Mapped[str] = mapped_column(String(80), default="", index=True)
    workflow_type: Mapped[str] = mapped_column(String(32), default="coworker_plugin")
    plugin_code: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(64), default="embedded")
    status: Mapped[str] = mapped_column(String(32), default="accepted")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    request_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    response_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    endpoint: Mapped[SiteEmbeddedWorkflowEndpoint] = relationship("SiteEmbeddedWorkflowEndpoint", back_populates="invocations")
    site: Mapped[Site] = relationship("Site", back_populates="embedded_workflow_invocations")


class SiteAiCoworkerDeliveryProfile(Base):
    __tablename__ = "site_ai_coworker_delivery_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="telegram", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    min_severity: Mapped[str] = mapped_column(String(16), default="medium")
    delivery_mode: Mapped[str] = mapped_column(String(16), default="manual")
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    include_thai_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    webhook_url: Mapped[str] = mapped_column(String(2048), default="")
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="coworker_delivery_profiles")

    __table_args__ = (UniqueConstraint("site_id", "channel", name="uq_site_ai_coworker_delivery_profile"),)


class SiteAiCoworkerDeliveryEscalationPolicy(Base):
    __tablename__ = "site_ai_coworker_delivery_escalation_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    plugin_code: Mapped[str] = mapped_column(String(80), default="", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    escalate_after_minutes: Mapped[int] = mapped_column(Integer, default=15)
    max_escalation_count: Mapped[int] = mapped_column(Integer, default=2)
    fallback_channels_json: Mapped[str] = mapped_column(Text, default="[]")
    escalate_on_statuses_json: Mapped[str] = mapped_column(Text, default="[]")
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="coworker_delivery_escalation_policies")

    __table_args__ = (UniqueConstraint("site_id", "plugin_code", name="uq_site_ai_coworker_delivery_escalation_policy"),)


class AiCoworkerDeliveryEvent(Base):
    __tablename__ = "ai_coworker_delivery_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    plugin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_coworker_plugins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), default="telegram", index=True)
    status: Mapped[str] = mapped_column(String(32), default="dry_run")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    title: Mapped[str] = mapped_column(String(255), default="")
    preview_text: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(128), default="coworker_delivery_ai")
    response_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="coworker_delivery_events")
    plugin: Mapped[AiCoworkerPlugin | None] = relationship("AiCoworkerPlugin")


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


class RedShadowPentestPolicy(Base):
    __tablename__ = "red_shadow_pentest_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    crawl_depth: Mapped[int] = mapped_column(Integer, default=2)
    max_pages: Mapped[int] = mapped_column(Integer, default=12)
    change_threshold: Mapped[int] = mapped_column(Integer, default=2)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=180)
    auto_assign_zero_day_pack: Mapped[bool] = mapped_column(Boolean, default=True)
    route_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_shadow_pentest_policies")

    __table_args__ = (UniqueConstraint("site_id", name="uq_red_shadow_pentest_policy"),)


class RedShadowPentestRun(Base):
    __tablename__ = "red_shadow_pentest_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    site_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    content_hash: Mapped[str] = mapped_column(String(128), default="")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    new_page_count: Mapped[int] = mapped_column(Integer, default=0)
    removed_page_count: Mapped[int] = mapped_column(Integer, default=0)
    changed_page_count: Mapped[int] = mapped_column(Integer, default=0)
    assigned_pack_code: Mapped[str] = mapped_column(String(80), default="")
    assigned_pack_category: Mapped[str] = mapped_column(String(64), default="")
    alert_routed: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_shadow_pentest_runs")


class RedSocialEngineeringRun(Base):
    __tablename__ = "red_social_engineering_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    campaign_name: Mapped[str] = mapped_column(String(255), default="thai_phishing_awareness")
    employee_segment: Mapped[str] = mapped_column(String(128), default="all_staff")
    language: Mapped[str] = mapped_column(String(32), default="th")
    difficulty: Mapped[str] = mapped_column(String(32), default="medium")
    impersonation_brand: Mapped[str] = mapped_column(String(128), default="")
    email_count: Mapped[int] = mapped_column(Integer, default=50)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")
    summary_th: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_social_engineering_runs")
    execution: Mapped[RedSocialCampaignExecution | None] = relationship(
        "RedSocialCampaignExecution",
        back_populates="run",
        cascade="all, delete-orphan",
        uselist=False,
    )


class RedSocialRosterEntry(Base):
    __tablename__ = "red_social_roster_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    employee_code: Mapped[str] = mapped_column(String(64), default="")
    full_name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), index=True)
    department: Mapped[str] = mapped_column(String(128), default="")
    role_title: Mapped[str] = mapped_column(String(128), default="")
    locale: Mapped[str] = mapped_column(String(32), default="th")
    risk_level: Mapped[str] = mapped_column(String(16), default="medium")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_social_roster_entries")
    recipients: Mapped[list[RedSocialCampaignRecipient]] = relationship(
        "RedSocialCampaignRecipient",
        back_populates="roster_entry",
    )

    __table_args__ = (UniqueConstraint("site_id", "email", name="uq_red_social_roster_site_email"),)


class RedSocialCampaignPolicy(Base):
    __tablename__ = "red_social_campaign_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    connector_type: Mapped[str] = mapped_column(String(32), default="simulated")
    sender_name: Mapped[str] = mapped_column(String(128), default="Security Awareness AI")
    sender_email: Mapped[str] = mapped_column(String(255), default="security-awareness@example.local")
    subject_prefix: Mapped[str] = mapped_column(String(64), default="[Awareness]")
    landing_base_url: Mapped[str] = mapped_column(String(1024), default="")
    report_mailbox: Mapped[str] = mapped_column(String(255), default="")
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_open_tracking: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_click_tracking: Mapped[bool] = mapped_column(Boolean, default=True)
    max_emails_per_run: Mapped[int] = mapped_column(Integer, default=200)
    kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_domains_json: Mapped[str] = mapped_column(Text, default="[]")
    connector_config_json: Mapped[str] = mapped_column(Text, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_social_campaign_policies")

    __table_args__ = (UniqueConstraint("site_id", name="uq_red_social_campaign_policy_site"),)


class RedSocialCampaignExecution(Base):
    __tablename__ = "red_social_campaign_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("red_social_engineering_runs.id", ondelete="CASCADE"),
        index=True,
    )
    connector_type: Mapped[str] = mapped_column(String(32), default="simulated")
    status: Mapped[str] = mapped_column(String(32), default="preview")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    requested_by: Mapped[str] = mapped_column(String(128), default="red_social_sim_ai")
    reviewed_by: Mapped[str] = mapped_column(String(128), default="")
    review_note: Mapped[str] = mapped_column(Text, default="")
    dispatch_mode: Mapped[str] = mapped_column(String(32), default="dry_run")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    killed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    killed_by: Mapped[str] = mapped_column(String(128), default="")
    kill_reason: Mapped[str] = mapped_column(Text, default="")
    connector_config_json: Mapped[str] = mapped_column(Text, default="{}")
    telemetry_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_social_campaign_executions")
    run: Mapped[RedSocialEngineeringRun] = relationship("RedSocialEngineeringRun", back_populates="execution")
    recipients: Mapped[list[RedSocialCampaignRecipient]] = relationship(
        "RedSocialCampaignRecipient",
        back_populates="execution",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("run_id", name="uq_red_social_campaign_execution_run"),)


class RedSocialCampaignRecipient(Base):
    __tablename__ = "red_social_campaign_recipients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("red_social_engineering_runs.id", ondelete="CASCADE"),
        index=True,
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("red_social_campaign_executions.id", ondelete="CASCADE"),
        index=True,
    )
    roster_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("red_social_roster_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(255), default="", index=True)
    recipient_name: Mapped[str] = mapped_column(String(255), default="")
    department: Mapped[str] = mapped_column(String(128), default="")
    delivery_status: Mapped[str] = mapped_column(String(32), default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telemetry_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_social_campaign_recipients")
    execution: Mapped[RedSocialCampaignExecution] = relationship("RedSocialCampaignExecution", back_populates="recipients")
    roster_entry: Mapped[RedSocialRosterEntry | None] = relationship("RedSocialRosterEntry", back_populates="recipients")
    run: Mapped[RedSocialEngineeringRun] = relationship("RedSocialEngineeringRun")


class RedVulnerabilityFinding(Base):
    __tablename__ = "red_vulnerability_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    source_tool: Mapped[str] = mapped_column(String(32), default="generic", index=True)
    source_finding_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    cve_id: Mapped[str] = mapped_column(String(80), default="")
    asset: Mapped[str] = mapped_column(String(255), default="")
    endpoint: Mapped[str] = mapped_column(String(1024), default="")
    status: Mapped[str] = mapped_column(String(32), default="imported")
    import_count: Mapped[int] = mapped_column(Integer, default=1)
    exploitability_score: Mapped[int] = mapped_column(Integer, default=0)
    false_positive_score: Mapped[int] = mapped_column(Integer, default=0)
    verdict: Mapped[str] = mapped_column(String(32), default="pending_validation")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    remediation_summary: Mapped[str] = mapped_column(Text, default="")
    raw_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    normalized_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    validation_details_json: Mapped[str] = mapped_column(Text, default="{}")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_vulnerability_findings")

    __table_args__ = (UniqueConstraint("site_id", "fingerprint", name="uq_red_vulnerability_finding_site_fingerprint"),)


class RedVulnerabilityValidationRun(Base):
    __tablename__ = "red_vulnerability_validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    actor: Mapped[str] = mapped_column(String(128), default="red_vuln_validator_ai")
    source_tools_json: Mapped[str] = mapped_column(Text, default="[]")
    finding_count: Mapped[int] = mapped_column(Integer, default=0)
    validated_count: Mapped[int] = mapped_column(Integer, default=0)
    exploitable_count: Mapped[int] = mapped_column(Integer, default=0)
    false_positive_count: Mapped[int] = mapped_column(Integer, default=0)
    needs_review_count: Mapped[int] = mapped_column(Integer, default=0)
    summary_th: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="red_vulnerability_validation_runs")


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


class BlueThreatLocalizerRun(Base):
    __tablename__ = "blue_threat_localizer_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    focus_region: Mapped[str] = mapped_column(String(64), default="thailand")
    sector: Mapped[str] = mapped_column(String(64), default="general")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_tier: Mapped[str] = mapped_column(String(16), default="low")
    headline: Mapped[str] = mapped_column(String(255), default="")
    summary_th: Mapped[str] = mapped_column(Text, default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_threat_localizer_runs")


class BlueThreatLocalizerPolicy(Base):
    __tablename__ = "blue_threat_localizer_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    focus_region: Mapped[str] = mapped_column(String(64), default="thailand")
    sector: Mapped[str] = mapped_column(String(64), default="general")
    subscribed_categories_json: Mapped[str] = mapped_column(Text, default='["identity","phishing","ransomware","web"]')
    recurring_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=240)
    min_feed_priority: Mapped[str] = mapped_column(String(16), default="medium")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_threat_localizer_policies")

    __table_args__ = (UniqueConstraint("site_id", name="uq_blue_threat_localizer_policy_site"),)


class BlueThreatLocalizerRoutingPolicy(Base):
    __tablename__ = "blue_threat_localizer_routing_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    stakeholder_groups_json: Mapped[str] = mapped_column(Text, default='["soc_l1","threat_hunting","security_lead"]')
    group_channel_map_json: Mapped[str] = mapped_column(Text, default='{"soc_l1":["telegram"],"threat_hunting":["teams"],"security_lead":["line"]}')
    category_group_map_json: Mapped[str] = mapped_column(Text, default='{"identity":["soc_l1","security_lead"],"phishing":["soc_l1"],"web":["threat_hunting"],"ransomware":["threat_hunting","security_lead"],"malware":["threat_hunting"],"insider":["security_lead"]}')
    min_priority_score: Mapped[int] = mapped_column(Integer, default=60)
    min_risk_tier: Mapped[str] = mapped_column(String(16), default="high")
    auto_promote_on_gap: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_apply_autotune: Mapped[bool] = mapped_column(Boolean, default=False)
    dispatch_via_action_center: Mapped[bool] = mapped_column(Boolean, default=True)
    playbook_promotion_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("site_id", name="uq_blue_threat_localizer_routing_policy_site"),)


class BlueThreatLocalizerPromotionRun(Base):
    __tablename__ = "blue_threat_localizer_promotion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    localizer_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blue_threat_localizer_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="ok")
    promoted_categories_json: Mapped[str] = mapped_column(Text, default="[]")
    routed_groups_json: Mapped[str] = mapped_column(Text, default="[]")
    playbook_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    autotune_run_id: Mapped[str] = mapped_column(String(64), default="")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    actor: Mapped[str] = mapped_column(String(128), default="blue_threat_promotion_ai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BlueThreatFeedItem(Base):
    __tablename__ = "blue_threat_feed_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name: Mapped[str] = mapped_column(String(64), default="manual", index=True)
    source_item_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    summary_th: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(32), default="identity", index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    focus_region: Mapped[str] = mapped_column(String(64), default="thailand", index=True)
    sectors_json: Mapped[str] = mapped_column(Text, default='["general"]')
    iocs_json: Mapped[str] = mapped_column(Text, default="[]")
    references_json: Mapped[str] = mapped_column(Text, default="[]")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("source_name", "source_item_id", name="uq_blue_threat_feed_item_source"),)


class BlueManagedResponderPolicy(Base):
    __tablename__ = "blue_managed_responder_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    min_severity: Mapped[str] = mapped_column(String(16), default="medium")
    action_mode: Mapped[str] = mapped_column(String(32), default="ai_recommended")
    dispatch_playbook: Mapped[bool] = mapped_column(Boolean, default=True)
    playbook_code: Mapped[str] = mapped_column(String(80), default="block-ip-and-waf-tighten")
    require_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    dry_run_default: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_managed_responder_policies")

    __table_args__ = (UniqueConstraint("site_id", name="uq_blue_managed_responder_policy"),)


class BlueManagedResponderRun(Base):
    __tablename__ = "blue_managed_responder_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blue_event_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="dry_run")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    selected_severity: Mapped[str] = mapped_column(String(16), default="low")
    selected_action: Mapped[str] = mapped_column(String(32), default="notify_team")
    playbook_code: Mapped[str] = mapped_column(String(80), default="")
    playbook_execution_id: Mapped[str] = mapped_column(String(64), default="")
    action_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    playbook_dispatched: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="blue_managed_responder_runs")
    event: Mapped[BlueEventLog | None] = relationship("BlueEventLog")


class BlueManagedResponderCallbackEvent(Base):
    __tablename__ = "blue_managed_responder_callback_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blue_managed_responder_runs.id", ondelete="CASCADE"),
        index=True,
    )
    connector_source: Mapped[str] = mapped_column(String(64), index=True, default="generic")
    contract_code: Mapped[str] = mapped_column(String(128), default="")
    callback_type: Mapped[str] = mapped_column(String(32), default="result_confirmed")
    webhook_event_id: Mapped[str] = mapped_column(String(255), default="")
    external_action_ref: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="received")
    actor: Mapped[str] = mapped_column(String(128), default="vendor_callback")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


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


class PurpleRoiDashboardSnapshot(Base):
    __tablename__ = "purple_roi_dashboard_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    lookback_days: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    site: Mapped[Site] = relationship("Site", back_populates="purple_roi_dashboard_snapshots")


class PurpleReportRelease(Base):
    __tablename__ = "purple_report_releases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    report_kind: Mapped[str] = mapped_column(String(64), index=True, default="incident_report")
    export_format: Mapped[str] = mapped_column(String(32), default="pdf")
    title: Mapped[str] = mapped_column(String(255), default="")
    filename: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending_approval")
    requested_by: Mapped[str] = mapped_column(String(128), default="purple_ai")
    approved_by: Mapped[str] = mapped_column(String(128), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PurpleAttackLayerWorkspace(Base):
    __tablename__ = "purple_attack_layer_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    layer_name: Mapped[str] = mapped_column(String(255), default="")
    source_kind: Mapped[str] = mapped_column(String(32), default="imported")
    actor: Mapped[str] = mapped_column(String(128), default="purple_operator")
    title: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    layer_json: Mapped[str] = mapped_column(Text, default="{}")
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


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


class SoarExecutionConnectorResult(Base):
    __tablename__ = "soar_execution_connector_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("soar_playbook_executions.id", ondelete="CASCADE"),
        index=True,
    )
    connector_source: Mapped[str] = mapped_column(String(64), index=True, default="generic")
    contract_code: Mapped[str] = mapped_column(String(128), default="")
    external_action_ref: Mapped[str] = mapped_column(String(255), default="")
    webhook_event_id: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="received")
    actor: Mapped[str] = mapped_column(String(128), default="connector_callback")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


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


class BlueLogRefinerPolicy(Base):
    __tablename__ = "blue_log_refiner_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="generic")
    execution_mode: Mapped[str] = mapped_column(String(16), default="pre_ingest")
    lookback_limit: Mapped[int] = mapped_column(Integer, default=200)
    min_keep_severity: Mapped[str] = mapped_column(String(16), default="medium")
    drop_recommendation_codes_json: Mapped[str] = mapped_column(Text, default='["ignore"]')
    target_noise_reduction_pct: Mapped[int] = mapped_column(Integer, default=80)
    average_event_size_kb: Mapped[int] = mapped_column(Integer, default=4)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("site_id", "connector_source", name="uq_blue_log_refiner_policy_site_source"),)


class BlueLogRefinerRun(Base):
    __tablename__ = "blue_log_refiner_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="generic")
    execution_mode: Mapped[str] = mapped_column(String(16), default="pre_ingest")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    kept_events: Mapped[int] = mapped_column(Integer, default=0)
    dropped_events: Mapped[int] = mapped_column(Integer, default=0)
    feedback_adjusted_events: Mapped[int] = mapped_column(Integer, default=0)
    noise_reduction_pct: Mapped[int] = mapped_column(Integer, default=0)
    estimated_storage_saved_kb: Mapped[int] = mapped_column(Integer, default=0)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BlueLogRefinerFeedback(Base):
    __tablename__ = "blue_log_refiner_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blue_log_refiner_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    connector_source: Mapped[str] = mapped_column(String(64), default="generic")
    event_type: Mapped[str] = mapped_column(String(64), default="")
    recommendation_code: Mapped[str] = mapped_column(String(64), default="")
    feedback_type: Mapped[str] = mapped_column(String(32), default="keep_signal")
    note: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(128), default="analyst")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BlueLogRefinerSchedulePolicy(Base):
    __tablename__ = "blue_log_refiner_schedule_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    connector_source: Mapped[str] = mapped_column(String(64), default="generic")
    schedule_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    dry_run_default: Mapped[bool] = mapped_column(Boolean, default=True)
    callback_ingest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), default="security")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("site_id", "connector_source", name="uq_blue_log_refiner_schedule_policy_site_source"),)


class BlueLogRefinerCallbackEvent(Base):
    __tablename__ = "blue_log_refiner_callback_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blue_log_refiner_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    connector_source: Mapped[str] = mapped_column(String(64), default="generic")
    callback_type: Mapped[str] = mapped_column(String(32), default="stream_result")
    source_system: Mapped[str] = mapped_column(String(64), default="")
    external_run_ref: Mapped[str] = mapped_column(String(128), default="")
    webhook_event_id: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="ok")
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    kept_events: Mapped[int] = mapped_column(Integer, default=0)
    dropped_events: Mapped[int] = mapped_column(Integer, default=0)
    noise_reduction_pct: Mapped[int] = mapped_column(Integer, default=0)
    estimated_storage_saved_kb: Mapped[int] = mapped_column(Integer, default=0)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    actor: Mapped[str] = mapped_column(String(128), default="siem_callback")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
