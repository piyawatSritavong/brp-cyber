/**
 * Demo / fallback data used when the backend API is unreachable.
 * Pre-seeded with duck-sec-ai.vercel.app as the default site.
 */
import type {
  SiteListResponse,
  SiteRedScanResponse,
  SiteBlueEventHistoryResponse,
  SiteUpsertResponse,
} from "./types";

const NOW = new Date().toISOString();

export const DEMO_SITE_ID = "demo-duck-sec-ai-01";

export const DEMO_SITE_LIST: SiteListResponse = {
  count: 1,
  rows: [
    {
      site_id: DEMO_SITE_ID,
      tenant_id: "tenant-demo",
      tenant_code: "tenant-01",
      site_code: "duck-sec-ai",
      display_name: "Duck Sec AI (Vercel)",
      base_url: "https://duck-sec-ai.vercel.app",
      is_active: true,
      config: {},
      created_at: NOW,
      updated_at: NOW,
    },
  ],
};

export const DEMO_SCAN_RESULT: SiteRedScanResponse = {
  status: "completed",
  scan_id: "scan-demo-001",
  scan_type: "full",
  ai_summary:
    "Scout Agent สแกน duck-sec-ai.vercel.app เสร็จสิ้น · พบช่องโหว่ระดับ Medium 2 รายการ และ Low 3 รายการ แนะนำให้เพิ่ม Security Headers และทบทวน CORS Policy ก่อน Production",
  findings: [
    {
      severity: "medium",
      type: "Missing Content-Security-Policy",
      description:
        "Content-Security-Policy header ไม่ได้ถูกตั้งค่า ทำให้มีความเสี่ยงต่อ XSS และ Content Injection attacks",
      recommendation:
        "เพิ่ม Content-Security-Policy ใน vercel.json headers section เช่น default-src 'self'",
    },
    {
      severity: "medium",
      type: "Open CORS Policy",
      description:
        "Access-Control-Allow-Origin: * พบใน /api endpoints อาจทำให้ข้อมูลถูกอ่านจาก Origin อื่นได้",
      recommendation:
        "จำกัด CORS ให้เฉพาะ Origin ที่เชื่อถือได้ เช่น https://duck-sec-ai.vercel.app",
    },
    {
      severity: "low",
      type: "Missing X-Frame-Options",
      description: "X-Frame-Options ไม่ถูกตั้งค่า เสี่ยงต่อ Clickjacking attacks",
      recommendation: "เพิ่ม X-Frame-Options: DENY ใน response headers",
    },
    {
      severity: "low",
      type: "Missing Permissions-Policy",
      description: "Permissions-Policy header ไม่ถูกตั้งค่า Browser API เช่น Camera/Mic เปิดอยู่",
      recommendation: "เพิ่ม Permissions-Policy: camera=(), microphone=(), geolocation=()",
    },
    {
      severity: "info",
      type: "SSL/TLS Valid",
      description:
        "TLS 1.3 ถูกใช้งาน Certificate ถูกต้องจาก Let's Encrypt · ยังไม่หมดอายุ",
    },
  ] as unknown as Record<string, unknown>,
};

export const DEMO_CODE_SCAN_RESULT: SiteRedScanResponse = {
  status: "completed",
  scan_id: "scan-code-demo-001",
  scan_type: "code_review",
  ai_summary:
    "Scout Agent วิเคราะห์ Code เสร็จสิ้น · พบช่องโหว่ที่ควรแก้ไข 3 รายการ ระดับ Critical 1 · Medium 2",
  findings: [
    {
      severity: "critical",
      type: "SQL Injection",
      line: 4,
      description:
        "การต่อ String ตรงๆ ใน Query โดยไม่ใช้ Parameterized Query ทำให้เสี่ยงต่อ SQL Injection อย่างมาก",
      recommendation: "ใช้ Prepared Statements หรือ ORM เช่น db.query('SELECT * FROM users WHERE id = ?', [id])",
    },
    {
      severity: "medium",
      type: "Missing Input Validation",
      line: 2,
      description: "ไม่มีการ Validate หรือ Sanitize input ก่อนนำไปใช้",
      recommendation: "เพิ่ม input validation เช่น parseInt() สำหรับ numeric ID และ escape สำหรับ string",
    },
    {
      severity: "medium",
      type: "Error Information Disclosure",
      description: "Error message อาจเปิดเผยข้อมูล Database structure ให้ผู้โจมตี",
      recommendation: "ใช้ Generic error message ในฝั่ง Production และ Log รายละเอียดไว้ที่ server side",
    },
  ] as unknown as Record<string, unknown>,
};

export const DEMO_BLUE_EVENTS: SiteBlueEventHistoryResponse = {
  count: 3,
  rows: [
    {
      event_id: "evt-demo-001",
      event_type: "failed_login_attempt",
      source_ip: "185.220.101.32",
      payload: { attempts: 12, user_agent: "Python-httpx/0.24.0", path: "/api/auth/login" },
      ai_severity: "high",
      ai_recommendation:
        "IP นี้ปรากฏใน Tor Exit Node list แนะนำให้ Block ทันทีและแจ้ง User ที่ถูก Target",
      status: "detected",
      action_taken: "logged",
      created_at: NOW,
    },
    {
      event_id: "evt-demo-002",
      event_type: "port_scan",
      source_ip: "45.142.212.100",
      payload: { ports_scanned: [22, 80, 443, 3306, 8080], scan_type: "SYN" },
      ai_severity: "medium",
      ai_recommendation:
        "พบ Port Scan จาก IP ในรัสเซีย ตรวจสอบว่าไม่มีบริการที่ไม่จำเป็นเปิดอยู่",
      status: "detected",
      action_taken: "rate_limited",
      created_at: NOW,
    },
    {
      event_id: "evt-demo-003",
      event_type: "suspicious_user_agent",
      source_ip: "91.108.4.55",
      payload: { user_agent: "sqlmap/1.7.8", path: "/api/search" },
      ai_severity: "high",
      ai_recommendation:
        "User Agent ตรงกับ SQLMap scanner แนะนำให้ Block IP และตรวจสอบ Database query logs",
      status: "blocked",
      action_taken: "blocked",
      created_at: NOW,
    },
  ],
};

export function makeDemoUpsertSite(payload: {
  tenant_code: string;
  site_code: string;
  display_name: string;
  base_url: string;
  is_active?: boolean;
  config?: Record<string, unknown>;
}): SiteUpsertResponse {
  return {
    status: "ok",
    site: {
      site_id: `site-${Date.now()}`,
      tenant_id: "tenant-demo",
      tenant_code: payload.tenant_code,
      site_code: payload.site_code,
      display_name: payload.display_name,
      base_url: payload.base_url,
      is_active: payload.is_active ?? true,
      config: payload.config ?? {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  };
}
