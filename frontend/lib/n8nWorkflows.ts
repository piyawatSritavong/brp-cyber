/** Visual node definitions + downloadable n8n JSON for each agent workflow */

export type WFNode = {
  id: string;
  icon: string;
  label: string;
  type: "trigger" | "ai" | "tool" | "condition" | "output";
};

export type AgentWorkflow = {
  agentId: "red" | "blue" | "purple" | "orchestrator";
  color: string;
  name: string;
  description: string;
  nodes: WFNode[];
  json: object; // n8n-importable workflow JSON
};

// ─── Helper — base HTTP node ─────────────────────────────────────────────────
function httpNode(id: string, name: string, url: string, method: "GET" | "POST", x: number, y: number) {
  return {
    id,
    name,
    type: "n8n-nodes-base.httpRequest",
    typeVersion: 4.2,
    position: [x, y],
    parameters: {
      method,
      url,
      authentication: "genericCredentialType",
      genericAuthType: "httpHeaderAuth",
      sendHeaders: true,
      headerParameters: {
        parameters: [{ name: "Authorization", value: "Bearer {{$env.CW_BEARER}}" }],
      },
    },
  };
}

function ollamaNode(id: string, x: number, y: number) {
  return {
    id,
    name: "Ollama (llama3.2)",
    type: "@n8n/n8n-nodes-langchain.lmOllama",
    typeVersion: 1,
    position: [x, y],
    parameters: { model: "llama3.2", baseUrl: "={{ $env.OLLAMA_URL || 'http://localhost:11434' }}" },
  };
}

// ─── Scout (Red) ──────────────────────────────────────────────────────────────
const SCOUT_WORKFLOW: AgentWorkflow = {
  agentId: "red",
  color: "#f31260",
  name: "Scout Agent — Red Team",
  description: "สแกนช่องโหว่อัตโนมัติทุก 6 ชั่วโมง, ยืนยัน CVE, แจ้งเตือน Slack เมื่อพบ Critical",
  nodes: [
    { id: "s1", icon: "⏱", label: "Schedule 6h", type: "trigger" },
    { id: "s2", icon: "📋", label: "Fetch Sites", type: "tool" },
    { id: "s3", icon: "🤖", label: "Scout AI", type: "ai" },
    { id: "s4", icon: "🔍", label: "Red Scan API", type: "tool" },
    { id: "s5", icon: "⚠️", label: "CVE Validator", type: "tool" },
    { id: "s6", icon: "❓", label: "Critical?", type: "condition" },
    { id: "s7", icon: "📢", label: "Slack Alert", type: "output" },
  ],
  json: {
    name: "CyberWitcher — Scout Agent (Red Team)",
    nodes: [
      {
        id: "s1",
        name: "Every 6 Hours",
        type: "n8n-nodes-base.scheduleTrigger",
        typeVersion: 1.2,
        position: [80, 300],
        parameters: { rule: { interval: [{ field: "hours", intervalValue: 6 }] } },
      },
      httpNode("s2", "Fetch Sites", "{{ $env.CW_API_URL }}/sites?limit=100", "GET", 280, 300),
      {
        id: "s3",
        name: "Scout AI Agent",
        type: "@n8n/n8n-nodes-langchain.agent",
        typeVersion: 1.7,
        position: [480, 300],
        parameters: {
          systemMessage:
            "You are the Scout (Red Team) agent. Analyze scan results, prioritize CVEs by CVSS score and business impact. Return JSON: {priority: 'critical'|'high'|'medium', cves: [], recommendation: ''}",
          options: { returnIntermediateSteps: false },
        },
      },
      ollamaNode("s3m", 480, 500),
      httpNode("s4", "Run Red Scan", "{{ $env.CW_API_URL }}/sites/{{ $json.site_id }}/red/scan", "POST", 680, 300),
      httpNode("s5", "CVE Validate", "{{ $env.CW_API_URL }}/sites/{{ $json.site_id }}/competitive/red/validate", "POST", 880, 300),
      {
        id: "s6",
        name: "Is Critical?",
        type: "n8n-nodes-base.if",
        typeVersion: 2,
        position: [1080, 300],
        parameters: {
          conditions: {
            options: { caseSensitive: false },
            conditions: [{ id: "c1", leftValue: "={{ $json.priority }}", operator: { type: "string", operation: "equals" }, rightValue: "critical" }],
          },
        },
      },
      {
        id: "s7",
        name: "Slack: Alert Security Team",
        type: "n8n-nodes-base.slack",
        typeVersion: 2.2,
        position: [1280, 200],
        parameters: {
          resource: "message",
          operation: "post",
          channel: "#security-alerts",
          text: "=🚨 *[Scout Agent]* Critical CVE detected on *{{ $json.site_id }}*\n\n{{ $json.recommendation }}",
        },
      },
      httpNode("s8", "Log to CyberWitcher", "{{ $env.CW_API_URL }}/events/ingest", "POST", 1280, 400),
    ],
    connections: {
      "Every 6 Hours": { main: [[{ node: "Fetch Sites", type: "main", index: 0 }]] },
      "Fetch Sites": { main: [[{ node: "Scout AI Agent", type: "main", index: 0 }]] },
      "Scout AI Agent": { main: [[{ node: "Run Red Scan", type: "main", index: 0 }]] },
      "Ollama (llama3.2)": { ai_languageModel: [[{ node: "Scout AI Agent", type: "ai_languageModel", index: 0 }]] },
      "Run Red Scan": { main: [[{ node: "CVE Validate", type: "main", index: 0 }]] },
      "CVE Validate": { main: [[{ node: "Is Critical?", type: "main", index: 0 }]] },
      "Is Critical?": {
        main: [
          [{ node: "Slack: Alert Security Team", type: "main", index: 0 }],
          [{ node: "Log to CyberWitcher", type: "main", index: 0 }],
        ],
      },
    },
    pinData: {},
    settings: { executionOrder: "v1" },
    meta: { templateCreatedBy: "CyberWitcher" },
  },
};

// ─── Guardian (Blue) ──────────────────────────────────────────────────────────
const GUARDIAN_WORKFLOW: AgentWorkflow = {
  agentId: "blue",
  color: "#006FEE",
  name: "Guardian Agent — Blue Team",
  description: "รับ Event Webhook จาก SIEM, วิเคราะห์ด้วย AI, Block IP อัตโนมัติ + แจ้งเตือนทีม",
  nodes: [
    { id: "g1", icon: "🪝", label: "CyberWitcher Webhook", type: "trigger" },
    { id: "g2", icon: "🤖", label: "Guardian AI", type: "ai" },
    { id: "g3", icon: "🔍", label: "Log Refiner", type: "tool" },
    { id: "g4", icon: "🕵️", label: "Threat Intel", type: "tool" },
    { id: "g5", icon: "❓", label: "High Risk?", type: "condition" },
    { id: "g6", icon: "🛡️", label: "Block IP", type: "output" },
    { id: "g7", icon: "📢", label: "LINE/Slack", type: "output" },
  ],
  json: {
    name: "CyberWitcher — Guardian Agent (Blue Team)",
    nodes: [
      {
        id: "g1",
        name: "CyberWitcher Event Webhook",
        type: "n8n-nodes-base.webhook",
        typeVersion: 2,
        position: [80, 300],
        webhookId: "cyberwitcher-blue-events",
        parameters: { httpMethod: "POST", path: "cyberwitcher-blue-events", responseMode: "onReceived", responseData: "firstEntryJson" },
      },
      {
        id: "g2",
        name: "Guardian AI Agent",
        type: "@n8n/n8n-nodes-langchain.agent",
        typeVersion: 1.7,
        position: [280, 300],
        parameters: {
          systemMessage:
            "You are the Guardian (Blue Team) agent. Analyze security events for real threats vs false positives. Score risk 0-100. Return JSON: {risk_score: number, is_threat: boolean, action: 'block'|'monitor'|'ignore', reason: ''}",
          options: {},
        },
      },
      ollamaNode("g2m", 280, 500),
      httpNode("g3", "Log Refiner API", "{{ $env.CW_API_URL }}/sites/{{ $json.body.site_id }}/blue/events?limit=50", "GET", 480, 300),
      httpNode("g4", "Threat Intel", "{{ $env.CW_API_URL }}/sites/{{ $json.body.site_id }}/competitive/blue/threat-intel", "POST", 680, 300),
      {
        id: "g5",
        name: "Is High Risk?",
        type: "n8n-nodes-base.if",
        typeVersion: 2,
        position: [880, 300],
        parameters: {
          conditions: {
            conditions: [{ id: "c1", leftValue: "={{ $json.is_threat }}", operator: { type: "boolean", operation: "true" } }],
          },
        },
      },
      httpNode("g6", "Block IP via CyberWitcher", "{{ $env.CW_API_URL }}/guardrails/block-ip", "POST", 1080, 200),
      {
        id: "g7",
        name: "Notify Team (Slack)",
        type: "n8n-nodes-base.slack",
        typeVersion: 2.2,
        position: [1080, 400],
        parameters: {
          resource: "message",
          operation: "post",
          channel: "#security-ops",
          text: "=🔵 *[Guardian Agent]* Threat Detected!\nSource IP: {{ $json.body.source_ip }}\nRisk Score: {{ $json.risk_score }}/100\nAction: {{ $json.action }}\nReason: {{ $json.reason }}",
        },
      },
    ],
    connections: {
      "CyberWitcher Event Webhook": { main: [[{ node: "Guardian AI Agent", type: "main", index: 0 }]] },
      "Guardian AI Agent": { main: [[{ node: "Log Refiner API", type: "main", index: 0 }]] },
      "Ollama (llama3.2)": { ai_languageModel: [[{ node: "Guardian AI Agent", type: "ai_languageModel", index: 0 }]] },
      "Log Refiner API": { main: [[{ node: "Threat Intel", type: "main", index: 0 }]] },
      "Threat Intel": { main: [[{ node: "Is High Risk?", type: "main", index: 0 }]] },
      "Is High Risk?": {
        main: [
          [{ node: "Block IP via CyberWitcher", type: "main", index: 0 }],
          [{ node: "Notify Team (Slack)", type: "main", index: 0 }],
        ],
      },
    },
    settings: { executionOrder: "v1" },
    meta: { templateCreatedBy: "CyberWitcher" },
  },
};

// ─── Architect (Purple) ───────────────────────────────────────────────────────
const ARCHITECT_WORKFLOW: AgentWorkflow = {
  agentId: "purple",
  color: "#9353d3",
  name: "Architect Agent — Purple Team",
  description: "สรุปผลประจำสัปดาห์: Correlation Red+Blue, ISO 27001 Gap, ร่าง Incident Report ส่ง Email",
  nodes: [
    { id: "p1", icon: "📅", label: "Weekly Trigger", type: "trigger" },
    { id: "p2", icon: "📥", label: "Fetch Red+Blue", type: "tool" },
    { id: "p3", icon: "🤖", label: "Architect AI", type: "ai" },
    { id: "p4", icon: "📊", label: "ISO Gap Check", type: "tool" },
    { id: "p5", icon: "✍️", label: "Draft Report", type: "tool" },
    { id: "p6", icon: "📧", label: "Send Report", type: "output" },
  ],
  json: {
    name: "CyberWitcher — Architect Agent (Purple Team)",
    nodes: [
      {
        id: "p1",
        name: "Weekly on Monday 08:00",
        type: "n8n-nodes-base.scheduleTrigger",
        typeVersion: 1.2,
        position: [80, 300],
        parameters: { rule: { interval: [{ field: "weeks", intervalValue: 1, triggerAtDay: [1], triggerAtHour: 8 }] } },
      },
      httpNode("p2a", "Fetch Red Results", "{{ $env.CW_API_URL }}/sites?limit=100", "GET", 280, 200),
      httpNode("p2b", "Fetch Blue Events", "{{ $env.CW_API_URL }}/governance/dashboard", "GET", 280, 400),
      {
        id: "p3",
        name: "Architect AI Agent",
        type: "@n8n/n8n-nodes-langchain.agent",
        typeVersion: 1.7,
        position: [480, 300],
        parameters: {
          systemMessage:
            "You are the Architect (Purple Team) agent. Correlate Red Team findings with Blue Team events. Identify attack chains, ISO 27001 gaps, and business risk. Return a structured executive summary in Thai and English.",
          options: {},
        },
      },
      ollamaNode("p3m", 480, 500),
      httpNode("p4", "ISO Gap Analysis", "{{ $env.CW_API_URL }}/purple/governance/gap-analysis", "POST", 680, 300),
      httpNode("p5", "Incident Ghostwriter", "{{ $env.CW_API_URL }}/purple/incident-report/draft", "POST", 880, 300),
      {
        id: "p6",
        name: "Email Weekly Report",
        type: "n8n-nodes-base.emailSend",
        typeVersion: 2.1,
        position: [1080, 300],
        parameters: {
          fromEmail: "security@company.com",
          toEmail: "ciso@company.com",
          subject: "=CyberWitcher — Weekly Security Brief ({{ $now.format('YYYY-MM-DD') }})",
          emailType: "html",
          message: "={{ $json.report_html }}",
        },
      },
    ],
    connections: {
      "Weekly on Monday 08:00": {
        main: [
          [{ node: "Fetch Red Results", type: "main", index: 0 }],
          [{ node: "Fetch Blue Events", type: "main", index: 0 }],
        ],
      },
      "Fetch Red Results": { main: [[{ node: "Architect AI Agent", type: "main", index: 0 }]] },
      "Fetch Blue Events": { main: [[{ node: "Architect AI Agent", type: "main", index: 1 }]] },
      "Ollama (llama3.2)": { ai_languageModel: [[{ node: "Architect AI Agent", type: "ai_languageModel", index: 0 }]] },
      "Architect AI Agent": { main: [[{ node: "ISO Gap Analysis", type: "main", index: 0 }]] },
      "ISO Gap Analysis": { main: [[{ node: "Incident Ghostwriter", type: "main", index: 0 }]] },
      "Incident Ghostwriter": { main: [[{ node: "Email Weekly Report", type: "main", index: 0 }]] },
    },
    settings: { executionOrder: "v1" },
    meta: { templateCreatedBy: "CyberWitcher" },
  },
};

// ─── Orchestrator ─────────────────────────────────────────────────────────────
const ORCHESTRATOR_WORKFLOW: AgentWorkflow = {
  agentId: "orchestrator",
  color: "#F76C45",
  name: "Orchestrator — Policy Gate",
  description: "กรองทุก Event จาก Agent, ผ่าน Policy Gate, Route งานไปยัง Agent ที่เหมาะสม + Audit Log",
  nodes: [
    { id: "o1", icon: "⚡", label: "All Events", type: "trigger" },
    { id: "o2", icon: "🔐", label: "Policy Gate", type: "condition" },
    { id: "o3", icon: "🤖", label: "Orchestrator AI", type: "ai" },
    { id: "o4", icon: "🔀", label: "Route Agent", type: "condition" },
    { id: "o5", icon: "✅", label: "Execute + Log", type: "output" },
  ],
  json: {
    name: "CyberWitcher — Orchestrator (Policy Gate)",
    nodes: [
      {
        id: "o1",
        name: "All CyberWitcher Events",
        type: "n8n-nodes-base.webhook",
        typeVersion: 2,
        position: [80, 300],
        webhookId: "cyberwitcher-orchestrator",
        parameters: { httpMethod: "POST", path: "cyberwitcher-orchestrator", responseMode: "onReceived" },
      },
      {
        id: "o2",
        name: "Policy Gate",
        type: "n8n-nodes-base.if",
        typeVersion: 2,
        position: [280, 300],
        parameters: {
          conditions: {
            conditions: [{ id: "c1", leftValue: "={{ $json.risk_score }}", operator: { type: "number", operation: "gt" }, rightValue: 60 }],
          },
        },
      },
      {
        id: "o3",
        name: "Orchestrator AI",
        type: "@n8n/n8n-nodes-langchain.agent",
        typeVersion: 1.7,
        position: [480, 200],
        parameters: {
          systemMessage:
            "You are the CyberWitcher Orchestrator. Decide which agent should handle this event (scout/guardian/architect) and what action to take. Consider policy constraints, risk score, and business impact. Return JSON: {agent: string, action: string, requires_human_approval: boolean}",
          options: {},
        },
      },
      ollamaNode("o3m", 480, 420),
      {
        id: "o4",
        name: "Route to Agent",
        type: "n8n-nodes-base.switch",
        typeVersion: 3,
        position: [680, 200],
        parameters: {
          mode: "expression",
          output: "={{ $json.agent }}",
          options: {},
        },
      },
      httpNode("o5a", "Trigger Scout Scan", "{{ $env.CW_API_URL }}/sites/{{ $json.site_id }}/red/scan", "POST", 880, 100),
      httpNode("o5b", "Trigger Guardian Block", "{{ $env.CW_API_URL }}/guardrails/block-ip", "POST", 880, 250),
      httpNode("o5c", "Trigger Architect Report", "{{ $env.CW_API_URL }}/purple/incident-report/draft", "POST", 880, 400),
      httpNode("o6", "Audit Log", "{{ $env.CW_API_URL }}/events/ingest", "POST", 1080, 300),
    ],
    connections: {
      "All CyberWitcher Events": { main: [[{ node: "Policy Gate", type: "main", index: 0 }]] },
      "Policy Gate": {
        main: [
          [{ node: "Orchestrator AI", type: "main", index: 0 }],
          [{ node: "Audit Log", type: "main", index: 0 }],
        ],
      },
      "Ollama (llama3.2)": { ai_languageModel: [[{ node: "Orchestrator AI", type: "ai_languageModel", index: 0 }]] },
      "Orchestrator AI": { main: [[{ node: "Route to Agent", type: "main", index: 0 }]] },
      "Route to Agent": {
        main: [
          [{ node: "Trigger Scout Scan", type: "main", index: 0 }],
          [{ node: "Trigger Guardian Block", type: "main", index: 0 }],
          [{ node: "Trigger Architect Report", type: "main", index: 0 }],
        ],
      },
    },
    settings: { executionOrder: "v1" },
    meta: { templateCreatedBy: "CyberWitcher" },
  },
};

export const AGENT_WORKFLOWS: AgentWorkflow[] = [
  SCOUT_WORKFLOW,
  GUARDIAN_WORKFLOW,
  ARCHITECT_WORKFLOW,
  ORCHESTRATOR_WORKFLOW,
];
