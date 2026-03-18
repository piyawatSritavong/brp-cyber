/** BRP Cyber — Workflow Canvas plugin catalog + default agent workflows */

export type PluginDef = {
  type: string;
  label: string;
  subtitle: string;
  icon: string;
  color: string;
  category: string;
  hasInput: boolean;
  hasOutput: boolean;
};

export type CanvasNode = {
  id: string;
  pluginType: string;
  label: string;
  icon: string;
  color: string;
  subtitle: string;
  x: number;
  y: number;
};

export type Edge = { id: string; from: string; to: string };

export type CanvasWorkflow = {
  name: string;
  active: boolean;
  nodes: CanvasNode[];
  edges: Edge[];
};

export type AgentId = "red" | "blue" | "purple" | "orchestrator";

// ─── BRP Plugin Catalog ───────────────────────────────────────────────────────
export const PLUGIN_CATALOG: PluginDef[] = [
  // Triggers
  { type: "trigger_schedule", label: "Schedule", subtitle: "Run on timer", icon: "⏱", color: "#17c964", category: "Triggers", hasInput: false, hasOutput: true },
  { type: "trigger_webhook", label: "BRP Webhook", subtitle: "On security event", icon: "🪝", color: "#17c964", category: "Triggers", hasInput: false, hasOutput: true },
  { type: "trigger_manual", label: "Manual Run", subtitle: "Trigger manually", icon: "▶️", color: "#17c964", category: "Triggers", hasInput: false, hasOutput: true },

  // Scout Agent (Red)
  { type: "red_scan", label: "Red Scan", subtitle: "Shadow Pentest", icon: "🔍", color: "#f31260", category: "Scout Agent", hasInput: true, hasOutput: true },
  { type: "red_cve", label: "CVE Validator", subtitle: "Auto-validate CVE", icon: "⚠️", color: "#f31260", category: "Scout Agent", hasInput: true, hasOutput: true },
  { type: "red_nuclei", label: "Nuclei Writer", subtitle: "YAML template gen", icon: "📝", color: "#f31260", category: "Scout Agent", hasInput: true, hasOutput: true },
  { type: "red_social", label: "Social Engineering", subtitle: "Phishing simulator", icon: "🎭", color: "#f31260", category: "Scout Agent", hasInput: true, hasOutput: true },
  { type: "red_exploit", label: "Exploit Generator", subtitle: "PoC script (lab only)", icon: "💥", color: "#f31260", category: "Scout Agent", hasInput: true, hasOutput: true },

  // Guardian Agent (Blue)
  { type: "blue_log", label: "Log Refiner", subtitle: "Filter noise events", icon: "🔬", color: "#006FEE", category: "Guardian Agent", hasInput: true, hasOutput: true },
  { type: "blue_responder", label: "Auto Responder", subtitle: "Block IP & contain", icon: "🛡️", color: "#006FEE", category: "Guardian Agent", hasInput: true, hasOutput: true },
  { type: "blue_intel", label: "Threat Intel", subtitle: "IOC + localization", icon: "🕵️", color: "#006FEE", category: "Guardian Agent", hasInput: true, hasOutput: true },
  { type: "blue_translate", label: "Alert Translator", subtitle: "Thai localization", icon: "🌐", color: "#006FEE", category: "Guardian Agent", hasInput: true, hasOutput: true },
  { type: "blue_playbook", label: "Auto Playbook", subtitle: "SOAR execution", icon: "📋", color: "#006FEE", category: "Guardian Agent", hasInput: true, hasOutput: true },

  // Architect Agent (Purple)
  { type: "purple_correlate", label: "Correlation", subtitle: "Red + Blue analysis", icon: "🔗", color: "#9353d3", category: "Architect Agent", hasInput: true, hasOutput: true },
  { type: "purple_iso", label: "ISO Gap Analysis", subtitle: "ISO 27001 / NIST CSF", icon: "📐", color: "#9353d3", category: "Architect Agent", hasInput: true, hasOutput: true },
  { type: "purple_report", label: "Incident Report", subtitle: "Ghostwriter", icon: "✍️", color: "#9353d3", category: "Architect Agent", hasInput: true, hasOutput: true },
  { type: "purple_mitre", label: "MITRE Heatmap", subtitle: "ATT&CK coverage", icon: "🗺️", color: "#9353d3", category: "Architect Agent", hasInput: true, hasOutput: true },
  { type: "purple_roi", label: "ROI Dashboard", subtitle: "Security ROI calc", icon: "📊", color: "#9353d3", category: "Architect Agent", hasInput: true, hasOutput: true },

  // Flow control
  { type: "flow_if", label: "If Condition", subtitle: "Branch on value", icon: "❓", color: "#f5a524", category: "Flow", hasInput: true, hasOutput: true },
  { type: "flow_switch", label: "Switch", subtitle: "Multi-path routing", icon: "🔀", color: "#f5a524", category: "Flow", hasInput: true, hasOutput: true },
  { type: "flow_wait", label: "Wait", subtitle: "Delay / debounce", icon: "⏳", color: "#f5a524", category: "Flow", hasInput: true, hasOutput: true },

  // Output
  { type: "output_slack", label: "Slack Alert", subtitle: "Post to channel", icon: "💬", color: "#4A154B", category: "Output", hasInput: true, hasOutput: false },
  { type: "output_email", label: "Email", subtitle: "Send report email", icon: "📧", color: "#6366f1", category: "Output", hasInput: true, hasOutput: false },
  { type: "output_block", label: "Block IP", subtitle: "Firewall API call", icon: "🚫", color: "#f5a524", category: "Output", hasInput: true, hasOutput: false },
  { type: "output_line", label: "LINE Notify", subtitle: "Thai notification", icon: "💚", color: "#00B900", category: "Output", hasInput: true, hasOutput: false },
  { type: "output_audit", label: "Audit Log", subtitle: "Write audit trail", icon: "📑", color: "#718096", category: "Output", hasInput: true, hasOutput: false },
];

export function getPlugin(type: string): PluginDef {
  return (
    PLUGIN_CATALOG.find((p) => p.type === type) ?? {
      type,
      label: type,
      subtitle: "",
      icon: "⚙️",
      color: "#718096",
      category: "Other",
      hasInput: true,
      hasOutput: true,
    }
  );
}

// ─── Default pre-loaded workflows per agent ───────────────────────────────────
export const DEFAULT_WORKFLOWS: Record<AgentId, CanvasWorkflow> = {
  red: {
    name: "Scout Agent (Red)",
    active: true,
    nodes: [
      { id: "r1", pluginType: "trigger_webhook", label: "BRP Webhook", icon: "🪝", color: "#17c964", subtitle: "On security event", x: 160, y: 260 },
      { id: "r2", pluginType: "red_scan", label: "Red Scan", icon: "🔍", color: "#f31260", subtitle: "Shadow Pentest", x: 420, y: 260 },
      { id: "r3", pluginType: "red_cve", label: "CVE Validator", icon: "⚠️", color: "#f31260", subtitle: "Auto-validate", x: 680, y: 260 },
      { id: "r4", pluginType: "flow_if", label: "Critical?", icon: "❓", color: "#f5a524", subtitle: "severity === critical", x: 940, y: 260 },
      { id: "r5", pluginType: "output_slack", label: "Slack Alert", icon: "💬", color: "#4A154B", subtitle: "#security-alerts", x: 1200, y: 160 },
      { id: "r6", pluginType: "output_audit", label: "Audit Log", icon: "📑", color: "#718096", subtitle: "Write audit trail", x: 1200, y: 360 },
    ],
    edges: [
      { id: "e1", from: "r1", to: "r2" },
      { id: "e2", from: "r2", to: "r3" },
      { id: "e3", from: "r3", to: "r4" },
      { id: "e4", from: "r4", to: "r5" },
      { id: "e5", from: "r4", to: "r6" },
    ],
  },

  blue: {
    name: "Guardian Agent (Blue)",
    active: true,
    nodes: [
      { id: "b1", pluginType: "trigger_webhook", label: "BRP Webhook", icon: "🪝", color: "#17c964", subtitle: "On security event", x: 160, y: 260 },
      { id: "b2", pluginType: "blue_log", label: "Log Refiner", icon: "🔬", color: "#006FEE", subtitle: "Filter noise events", x: 420, y: 260 },
      { id: "b3", pluginType: "blue_intel", label: "Threat Intel", icon: "🕵️", color: "#006FEE", subtitle: "IOC + localization", x: 680, y: 260 },
      { id: "b4", pluginType: "flow_if", label: "High Risk?", icon: "❓", color: "#f5a524", subtitle: "risk_score > 70", x: 940, y: 260 },
      { id: "b5", pluginType: "blue_responder", label: "Auto Responder", icon: "🛡️", color: "#006FEE", subtitle: "Block IP & contain", x: 1200, y: 160 },
      { id: "b6", pluginType: "output_line", label: "LINE Notify", icon: "💚", color: "#00B900", subtitle: "Thai notification", x: 1200, y: 360 },
    ],
    edges: [
      { id: "e1", from: "b1", to: "b2" },
      { id: "e2", from: "b2", to: "b3" },
      { id: "e3", from: "b3", to: "b4" },
      { id: "e4", from: "b4", to: "b5" },
      { id: "e5", from: "b4", to: "b6" },
    ],
  },

  purple: {
    name: "Architect Agent (Purple)",
    active: true,
    nodes: [
      { id: "p1", pluginType: "trigger_schedule", label: "Weekly Schedule", icon: "⏱", color: "#17c964", subtitle: "Every Monday 08:00", x: 160, y: 260 },
      { id: "p2", pluginType: "purple_correlate", label: "Correlation", icon: "🔗", color: "#9353d3", subtitle: "Red + Blue analysis", x: 420, y: 260 },
      { id: "p3", pluginType: "purple_iso", label: "ISO Gap Analysis", icon: "📐", color: "#9353d3", subtitle: "ISO 27001 / NIST CSF", x: 680, y: 260 },
      { id: "p4", pluginType: "purple_report", label: "Incident Report", icon: "✍️", color: "#9353d3", subtitle: "Ghostwriter", x: 940, y: 260 },
      { id: "p5", pluginType: "output_email", label: "Email CISO", icon: "📧", color: "#6366f1", subtitle: "Weekly brief", x: 1200, y: 260 },
    ],
    edges: [
      { id: "e1", from: "p1", to: "p2" },
      { id: "e2", from: "p2", to: "p3" },
      { id: "e3", from: "p3", to: "p4" },
      { id: "e4", from: "p4", to: "p5" },
    ],
  },

  orchestrator: {
    name: "Orchestrator",
    active: true,
    nodes: [
      { id: "o1", pluginType: "trigger_webhook", label: "All Events", icon: "🪝", color: "#17c964", subtitle: "Any agent event", x: 160, y: 300 },
      { id: "o2", pluginType: "flow_if", label: "Policy Gate", icon: "🔐", color: "#f5a524", subtitle: "risk_score > 60", x: 420, y: 300 },
      { id: "o3", pluginType: "red_scan", label: "Red Scan", icon: "🔍", color: "#f31260", subtitle: "Scout action", x: 700, y: 140 },
      { id: "o4", pluginType: "blue_responder", label: "Auto Responder", icon: "🛡️", color: "#006FEE", subtitle: "Guardian action", x: 700, y: 300 },
      { id: "o5", pluginType: "purple_report", label: "Incident Report", icon: "✍️", color: "#9353d3", subtitle: "Architect action", x: 700, y: 460 },
      { id: "o6", pluginType: "output_audit", label: "Audit Log", icon: "📑", color: "#718096", subtitle: "All outcomes", x: 980, y: 300 },
    ],
    edges: [
      { id: "e1", from: "o1", to: "o2" },
      { id: "e2", from: "o2", to: "o3" },
      { id: "e3", from: "o2", to: "o4" },
      { id: "e4", from: "o2", to: "o5" },
      { id: "e5", from: "o3", to: "o6" },
      { id: "e6", from: "o4", to: "o6" },
      { id: "e7", from: "o5", to: "o6" },
    ],
  },
};

export const AGENT_META: Record<AgentId, { color: string; label: string; icon: string }> = {
  red: { color: "#f31260", label: "Scout Agent", icon: "🔍" },
  blue: { color: "#006FEE", label: "Guardian Agent", icon: "🛡️" },
  purple: { color: "#9353d3", label: "Architect Agent", icon: "📐" },
  orchestrator: { color: "#F76C45", label: "Orchestrator", icon: "⚡" },
};
