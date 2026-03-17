"use client";

import { useCallback, useEffect, useState } from "react";
import { runSiteRedScan, fetchSites } from "@/lib/api";
import { EmptyStateCard } from "@/components/EmptyStateCard";
import type { SiteRedScanResponse, SiteRow } from "@/lib/types";

const LANGUAGES = [
  { value: "javascript", label: "JavaScript / TypeScript" },
  { value: "python", label: "Python" },
  { value: "go", label: "Go" },
  { value: "php", label: "PHP" },
  { value: "java", label: "Java" },
  { value: "ruby", label: "Ruby" },
  { value: "shell", label: "Shell / Bash" },
] as const;

const CODE_SAMPLES: Record<string, string> = {
  javascript: `// Example: SQL injection vulnerability
async function getUser(req, res) {
  const id = req.query.id;
  const query = "SELECT * FROM users WHERE id = " + id;  // ⚠️ Vulnerable
  const result = await db.query(query);
  res.json(result);
}`,
  python: `# Example: Command injection vulnerability
import subprocess

def run_command(user_input):
    cmd = f"echo {user_input}"  # ⚠️ Vulnerable
    subprocess.run(cmd, shell=True)`,
  php: `<?php
// Example: XSS vulnerability
$name = $_GET['name'];
echo "<h1>Hello " . $name . "</h1>"; // ⚠️ Vulnerable
?>`,
};

type FindingRow = {
  severity: string;
  type: string;
  line?: number;
  description: string;
  recommendation?: string;
};

export function CodeScannerPanel() {
  const [sites, setSites] = useState<SiteRow[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [codeInput, setCodeInput] = useState("");
  const [language, setLanguage] = useState<string>("javascript");
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<SiteRedScanResponse | null>(null);
  const [error, setError] = useState("");
  const [uploadedFilename, setUploadedFilename] = useState("");

  const loadSites = useCallback(async () => {
    try {
      const res = await fetchSites("", 100);
      setSites(res.rows || []);
      if (!selectedSiteId && res.rows.length > 0) {
        setSelectedSiteId(res.rows[0].site_id);
      }
    } catch {
      // silent
    }
  }, [selectedSiteId]);

  useEffect(() => { void loadSites(); }, [loadSites]);

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFilename(file.name);
    const reader = new FileReader();
    reader.onload = (evt) => {
      setCodeInput((evt.target?.result as string) ?? "");
    };
    reader.readAsText(file);
  }

  function loadSample() {
    setCodeInput(CODE_SAMPLES[language] ?? CODE_SAMPLES.javascript);
  }

  async function handleScan() {
    if (!codeInput.trim()) {
      setError("กรุณาใส่ Code ก่อนทำการ Scan");
      return;
    }
    if (!selectedSiteId) {
      setError("กรุณาเลือก Site ก่อนทำการ Scan (ต้องการ Site เพื่อเชื่อมต่อ API)");
      return;
    }

    setScanning(true);
    setError("");
    setScanResult(null);

    try {
      const res = await runSiteRedScan(selectedSiteId, {
        scan_type: "code_review",
        include_paths: [language],
      });
      setScanResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "scan_failed");
    } finally {
      setScanning(false);
    }
  }

  // Parse findings from result
  let findings: FindingRow[] = [];
  if (scanResult?.findings) {
    const raw = scanResult.findings;
    if (Array.isArray(raw)) {
      findings = raw as FindingRow[];
    } else if (typeof raw === "object") {
      findings = Object.entries(raw).map(([k, v]) => ({
        severity: "medium",
        type: k,
        description: typeof v === "string" ? v : JSON.stringify(v),
      }));
    }
  }

  const severityColor: Record<string, string> = {
    critical: "#f31260",
    high: "#f31260",
    medium: "#f5a623",
    low: "#17c964",
    info: "var(--accent)",
  };

  return (
    <main className="space-y-5">
      <section className="card p-5">
        <p className="text-xs uppercase tracking-[0.26em] text-accent">Developer Security</p>
        <h2 className="mt-1 text-[1.85rem] font-semibold text-ink">Code Scanner</h2>
        <p className="mt-1 text-sm text-slate-500">
          วาง Code หรืออัปโหลดไฟล์ — AI จะสแกนหาช่องโหว่ทันที เหมือนมี Security Expert นั่งข้างๆ
        </p>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Input panel */}
        <div className="card p-5 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-panelAlt/50 px-3 py-1.5 text-xs text-slate-500">
              Language
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="bg-transparent text-sm font-medium text-ink outline-none"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </label>

            {sites.length > 0 && (
              <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-panelAlt/50 px-3 py-1.5 text-xs text-slate-500">
                Site
                <select
                  value={selectedSiteId}
                  onChange={(e) => setSelectedSiteId(e.target.value)}
                  className="min-w-[120px] bg-transparent text-sm font-medium text-ink outline-none"
                >
                  {sites.map((s) => (
                    <option key={s.site_id} value={s.site_id}>{s.display_name}</option>
                  ))}
                </select>
              </label>
            )}

            <button
              type="button"
              onClick={loadSample}
              className="text-xs text-accent underline hover:opacity-75"
            >
              Load Sample
            </button>
          </div>

          <textarea
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)}
            placeholder={`วาง ${LANGUAGES.find((l) => l.value === language)?.label ?? "Code"} ที่นี่…`}
            className="code-textarea w-full"
            style={{ minHeight: 220 }}
          />

          <div className="flex items-center gap-3 flex-wrap">
            <label className="flex items-center gap-2 cursor-pointer rounded-xl border border-dashed border-slate-300 px-4 py-2 text-xs text-slate-500 hover:border-accent hover:text-accent transition-colors">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
              </svg>
              {uploadedFilename || "Upload File"}
              <input
                type="file"
                accept=".js,.ts,.jsx,.tsx,.py,.go,.php,.java,.rb,.sh"
                className="sr-only"
                onChange={handleFileUpload}
              />
            </label>

            <button
              type="button"
              onClick={() => void handleScan()}
              disabled={scanning || !codeInput.trim()}
              className="flex items-center gap-2 rounded-xl bg-accent px-5 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              {scanning ? (
                <>
                  <span className="agent-dot agent-dot-yellow" />
                  กำลัง Scan…
                </>
              ) : (
                <>
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 2 11 13M22 2 15 22l-4-9-9-4 20-7Z" />
                  </svg>
                  Scan for Vulnerabilities
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
              {error}
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="card flex flex-col">
          {!scanResult && !scanning && !error ? (
            <EmptyStateCard
              icon="code"
              title="รอ Scan ผล"
              body="วาง Code ทางซ้าย แล้วกด 'Scan for Vulnerabilities' — AI จะวิเคราะห์ช่องโหว่ใน Code ของคุณทันที"
            />
          ) : scanning ? (
            <div className="empty-state-card">
              <div className="empty-state-blob">
                <span className="text-2xl">🔍</span>
              </div>
              <p className="text-sm font-semibold text-ink">Scout Agent กำลังสแกน…</p>
              <p className="text-xs text-slate-400">AI กำลังวิเคราะห์ {language} code ของคุณ</p>
              <div className="chat-typing mt-2">
                <span /><span /><span />
              </div>
            </div>
          ) : scanResult ? (
            <div className="p-5 space-y-4 overflow-y-auto">
              <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3">
                <p className="text-xs font-semibold text-green-700 uppercase tracking-wider">AI Summary</p>
                <p className="mt-1 text-sm text-green-800 leading-relaxed">{scanResult.ai_summary || "Scan completed."}</p>
                <p className="mt-2 text-[11px] text-green-600">Scan ID: {scanResult.scan_id} · Status: {scanResult.status}</p>
              </div>

              {findings.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold text-ink mb-2">
                    Findings ({findings.length})
                  </p>
                  <div className="space-y-2">
                    {findings.map((f, i) => (
                      <div key={i} className="rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
                            style={{
                              color: severityColor[f.severity?.toLowerCase()] ?? "var(--accent)",
                              background: `${severityColor[f.severity?.toLowerCase()] ?? "var(--accent)"}18`,
                            }}
                          >
                            {f.severity || "medium"}
                          </span>
                          <span className="text-xs font-semibold text-ink">{f.type}</span>
                          {f.line && <span className="text-[10px] text-slate-400">Line {f.line}</span>}
                        </div>
                        <p className="text-xs text-slate-500 leading-relaxed">{f.description}</p>
                        {f.recommendation && (
                          <p className="mt-1 text-xs text-accent font-medium">💡 {f.recommendation}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-green-200 bg-green-50/60 p-4 text-center">
                  <p className="text-2xl mb-2">✅</p>
                  <p className="text-sm font-semibold text-green-700">ไม่พบช่องโหว่ที่ชัดเจน</p>
                  <p className="text-xs text-green-600 mt-1">Code ผ่าน Basic Security Check</p>
                </div>
              )}
            </div>
          ) : error ? (
            <EmptyStateCard
              icon="code"
              title="Scan ล้มเหลว"
              body={error}
              action={{ label: "ลองใหม่อีกครั้ง", onClick: () => { setError(""); setScanResult(null); } }}
            />
          ) : null}
        </div>
      </div>
    </main>
  );
}
