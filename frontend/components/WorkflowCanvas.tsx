"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  PLUGIN_CATALOG,
  DEFAULT_WORKFLOWS,
  getPlugin,
  type AgentId,
  type CanvasNode,
  type CanvasWorkflow,
  type Edge,
  type PluginDef,
} from "@/lib/workflowPlugins";

// ─── Constants ────────────────────────────────────────────────────────────────
const NW = 188; // node width
const NH = 68;  // node height
const CANVAS_W = 4800;
const CANVAS_H = 3000;

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

// ─── Bezier path from output port to input port ───────────────────────────────
function bezier(x1: number, y1: number, x2: number, y2: number): string {
  const dx = Math.max(60, Math.abs(x2 - x1) * 0.5);
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}

function outputPt(n: CanvasNode) {
  return { x: n.x + NW, y: n.y + NH / 2 };
}
function inputPt(n: CanvasNode) {
  return { x: n.x, y: n.y + NH / 2 };
}

// ─── Category icons ───────────────────────────────────────────────────────────
const CATEGORY_ICONS: Record<string, string> = {
  Triggers: "⚡",
  "Scout Agent": "🔍",
  "Guardian Agent": "🛡️",
  "Architect Agent": "📐",
  Flow: "🔀",
  Output: "📢",
};

// ─── Node box ─────────────────────────────────────────────────────────────────
type NodeBoxProps = {
  node: CanvasNode;
  selected: boolean;
  onPointerDown: (e: React.PointerEvent) => void;
  onOutputClick: (e: React.MouseEvent) => void;
  onInputClick: (e: React.MouseEvent) => void;
  onDelete: () => void;
  plugin: PluginDef;
};

function NodeBox({ node, selected, onPointerDown, onOutputClick, onInputClick, onDelete, plugin }: NodeBoxProps) {
  return (
    <div
      style={{
        position: "absolute",
        left: node.x,
        top: node.y,
        width: NW,
        height: NH,
        userSelect: "none",
        cursor: "grab",
      }}
      onPointerDown={onPointerDown}
    >
      {/* Input port */}
      {plugin.hasInput && (
        <div
          onClick={onInputClick}
          style={{
            position: "absolute",
            left: -8,
            top: NH / 2 - 8,
            width: 16,
            height: 16,
            borderRadius: "50%",
            background: "#2a2a3a",
            border: "2px solid #4a4a6a",
            cursor: "crosshair",
            zIndex: 10,
          }}
          title="Input port"
        />
      )}

      {/* Node body */}
      <div
        style={{
          width: "100%",
          height: "100%",
          background: selected ? "#25253a" : "#1c1c2c",
          border: `1.5px solid ${selected ? node.color : "#2d2d45"}`,
          borderRadius: 12,
          boxShadow: selected ? `0 0 0 2px ${node.color}44, 0 4px 20px rgba(0,0,0,0.5)` : "0 2px 8px rgba(0,0,0,0.4)",
          display: "flex",
          alignItems: "center",
          overflow: "hidden",
          transition: "border-color 0.15s, box-shadow 0.15s",
        }}
      >
        {/* Colored icon strip */}
        <div
          style={{
            width: 44,
            flexShrink: 0,
            height: "100%",
            background: `${node.color}22`,
            borderRight: `1px solid ${node.color}33`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 20,
          }}
        >
          {node.icon}
        </div>
        {/* Label + subtitle */}
        <div style={{ flex: 1, padding: "0 10px", minWidth: 0 }}>
          <p style={{ color: "#e2e8f0", fontSize: 12, fontWeight: 700, margin: 0, lineHeight: "1.3", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {node.label}
          </p>
          <p style={{ color: "#6b7280", fontSize: 10, margin: "2px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {node.subtitle}
          </p>
        </div>
        {/* Delete button (only when selected) */}
        {selected && (
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            style={{
              position: "absolute",
              top: -8,
              right: -8,
              width: 18,
              height: 18,
              borderRadius: "50%",
              background: "#ef4444",
              border: "none",
              color: "#fff",
              fontSize: 10,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1,
              zIndex: 20,
            }}
          >
            ×
          </button>
        )}
      </div>

      {/* Output port */}
      {plugin.hasOutput && (
        <div
          onClick={onOutputClick}
          style={{
            position: "absolute",
            right: -8,
            top: NH / 2 - 8,
            width: 16,
            height: 16,
            borderRadius: "50%",
            background: node.color,
            border: "2px solid #1c1c2c",
            cursor: "crosshair",
            zIndex: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Output port — click to connect"
        >
          <span style={{ color: "#fff", fontSize: 8, lineHeight: 1, fontWeight: 800 }}>+</span>
        </div>
      )}
    </div>
  );
}

// ─── Right catalog panel ──────────────────────────────────────────────────────
type CatalogProps = {
  search: string;
  onSearch: (v: string) => void;
  onAdd: (pluginType: string) => void;
};

function CatalogPanel({ search, onSearch, onAdd }: CatalogProps) {
  const filtered = search
    ? PLUGIN_CATALOG.filter(
        (p) =>
          p.label.toLowerCase().includes(search.toLowerCase()) ||
          p.subtitle.toLowerCase().includes(search.toLowerCase())
      )
    : PLUGIN_CATALOG;

  const categories = [...new Set(filtered.map((p) => p.category))];

  return (
    <div
      style={{
        width: 272,
        flexShrink: 0,
        background: "#16161f",
        borderLeft: "1px solid #2d2d45",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div style={{ padding: "14px 16px 10px", borderBottom: "1px solid #2d2d45" }}>
        <p style={{ color: "#e2e8f0", fontSize: 13, fontWeight: 700, margin: "0 0 10px" }}>
          What happens next?
        </p>
        <div style={{ position: "relative" }}>
          <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", fontSize: 13, color: "#6b7280" }}>🔍</span>
          <input
            type="text"
            placeholder="Search nodes..."
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            style={{
              width: "100%",
              background: "#0d0d17",
              border: "1px solid #2d2d45",
              borderRadius: 8,
              color: "#e2e8f0",
              fontSize: 12,
              padding: "7px 10px 7px 30px",
              outline: "none",
              boxSizing: "border-box",
            }}
          />
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
        {categories.map((cat) => (
          <div key={cat}>
            <p
              style={{
                color: "#6b7280",
                fontSize: 10,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.12em",
                padding: "8px 16px 4px",
                margin: 0,
              }}
            >
              {CATEGORY_ICONS[cat] ?? "•"} {cat}
            </p>
            {filtered
              .filter((p) => p.category === cat)
              .map((p) => (
                <button
                  key={p.type}
                  type="button"
                  onClick={() => onAdd(p.type)}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "7px 16px",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                    color: "inherit",
                    transition: "background 0.1s",
                  }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "#1e1e30")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
                >
                  <span
                    style={{
                      width: 30,
                      height: 30,
                      borderRadius: 8,
                      background: `${p.color}22`,
                      border: `1px solid ${p.color}44`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 15,
                      flexShrink: 0,
                    }}
                  >
                    {p.icon}
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <p style={{ color: "#e2e8f0", fontSize: 12, fontWeight: 600, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p.label}
                    </p>
                    <p style={{ color: "#6b7280", fontSize: 10, margin: "1px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {p.subtitle}
                    </p>
                  </div>
                  <span style={{ color: "#6b7280", fontSize: 14, flexShrink: 0 }}>›</span>
                </button>
              ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Top bar ──────────────────────────────────────────────────────────────────
type TopBarProps = {
  name: string;
  active: boolean;
  nodeCount: number;
  onNameChange: (v: string) => void;
  onToggleActive: () => void;
  onSave: () => void;
  onClear: () => void;
  saved: boolean;
};

function TopBar({ name, active, nodeCount, onNameChange, onToggleActive, onSave, onClear, saved }: TopBarProps) {
  return (
    <div
      style={{
        height: 52,
        flexShrink: 0,
        background: "#13131c",
        borderBottom: "1px solid #2d2d45",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: 12,
      }}
    >
      {/* Logo + name */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 18 }}>⚙️</span>
        <input
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          style={{
            background: "transparent",
            border: "none",
            color: "#e2e8f0",
            fontSize: 14,
            fontWeight: 700,
            outline: "none",
            minWidth: 0,
            flex: 1,
          }}
          spellCheck={false}
        />
        <span style={{ color: "#6b7280", fontSize: 11, flexShrink: 0 }}>
          {nodeCount} node{nodeCount !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Editor / Executions tabs */}
      <div style={{ display: "flex", background: "#1e1e2c", borderRadius: 8, overflow: "hidden", border: "1px solid #2d2d45" }}>
        {["Editor", "Executions"].map((t) => (
          <span
            key={t}
            style={{
              padding: "4px 12px",
              fontSize: 12,
              fontWeight: 600,
              color: t === "Editor" ? "#e2e8f0" : "#6b7280",
              background: t === "Editor" ? "#2d2d45" : "transparent",
              cursor: "pointer",
            }}
          >
            {t}
          </span>
        ))}
      </div>

      {/* Active toggle */}
      <div
        style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}
        onClick={onToggleActive}
      >
        <div
          style={{
            width: 36,
            height: 20,
            borderRadius: 10,
            background: active ? "#17c964" : "#2d2d45",
            position: "relative",
            transition: "background 0.2s",
          }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: "50%",
              background: "#fff",
              position: "absolute",
              top: 3,
              left: active ? 19 : 3,
              transition: "left 0.2s",
            }}
          />
        </div>
        <span style={{ color: active ? "#17c964" : "#6b7280", fontSize: 12, fontWeight: 600 }}>
          {active ? "Active" : "Inactive"}
        </span>
      </div>

      {/* Clear */}
      <button
        onClick={onClear}
        style={{
          background: "transparent",
          border: "1px solid #2d2d45",
          borderRadius: 8,
          color: "#6b7280",
          fontSize: 12,
          fontWeight: 600,
          padding: "5px 12px",
          cursor: "pointer",
        }}
      >
        Clear
      </button>

      {/* Save */}
      <button
        onClick={onSave}
        style={{
          background: saved ? "#17c964" : "#F76C45",
          border: "none",
          borderRadius: 8,
          color: "#fff",
          fontSize: 12,
          fontWeight: 700,
          padding: "6px 16px",
          cursor: "pointer",
          transition: "background 0.2s",
          minWidth: 72,
        }}
      >
        {saved ? "✓ Saved" : "Save"}
      </button>
    </div>
  );
}

// ─── Main WorkflowCanvas ──────────────────────────────────────────────────────
type Props = { agentId: AgentId };

export function WorkflowCanvas({ agentId }: Props) {
  const storageKey = `workflow-${agentId}`;

  function loadWorkflow(): CanvasWorkflow {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) return JSON.parse(raw) as CanvasWorkflow;
    } catch {
      // ignore
    }
    return structuredClone(DEFAULT_WORKFLOWS[agentId]);
  }

  const [workflow, setWorkflow] = useState<CanvasWorkflow>(loadWorkflow);
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [saved, setSaved] = useState(false);

  // Drag state
  const dragging = useRef<{ id: string; offsetX: number; offsetY: number } | null>(null);
  // Connect state
  const connecting = useRef<{ fromId: string } | null>(null);
  const [tempLine, setTempLine] = useState<{ x1: number; y1: number; x2: number; y2: number } | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);

  // ── Pointer capture drag ──
  useEffect(() => {
    if (!dragging.current) return;

    function onMove(e: PointerEvent) {
      if (!dragging.current || !canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left - dragging.current.offsetX;
      const y = e.clientY - rect.top - dragging.current.offsetY;
      setWorkflow((w) => ({
        ...w,
        nodes: w.nodes.map((n) => (n.id === dragging.current!.id ? { ...n, x: Math.max(0, x), y: Math.max(0, y) } : n)),
      }));

      // Update temp connection line if connecting
      if (connecting.current) {
        const fromNode = workflow.nodes.find((n) => n.id === connecting.current!.fromId);
        if (fromNode) {
          const op = outputPt(fromNode);
          setTempLine({ x1: op.x, y1: op.y, x2: e.clientX - rect.left, y2: e.clientY - rect.top });
        }
      }
    }

    function onUp() {
      dragging.current = null;
    }

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  });

  // Track mouse for temp connection line
  function handleCanvasMouseMove(e: React.MouseEvent) {
    if (!connecting.current || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const fromNode = workflow.nodes.find((n) => n.id === connecting.current!.fromId);
    if (!fromNode) return;
    const op = outputPt(fromNode);
    setTempLine({ x1: op.x, y1: op.y, x2: e.clientX - rect.left, y2: e.clientY - rect.top });
  }

  function handleCanvasClick() {
    if (connecting.current) {
      connecting.current = null;
      setTempLine(null);
      return;
    }
    setSelected(null);
  }

  function handleNodePointerDown(e: React.PointerEvent, nodeId: string) {
    e.stopPropagation();
    if (connecting.current) return;
    setSelected(nodeId);
    const node = workflow.nodes.find((n) => n.id === nodeId)!;
    const rect = canvasRef.current!.getBoundingClientRect();
    dragging.current = {
      id: nodeId,
      offsetX: e.clientX - rect.left - node.x,
      offsetY: e.clientY - rect.top - node.y,
    };
  }

  function handleOutputClick(e: React.MouseEvent, nodeId: string) {
    e.stopPropagation();
    connecting.current = { fromId: nodeId };
    const fromNode = workflow.nodes.find((n) => n.id === nodeId)!;
    const rect = canvasRef.current!.getBoundingClientRect();
    const op = outputPt(fromNode);
    setTempLine({ x1: op.x, y1: op.y, x2: op.x, y2: op.y });
  }

  function handleInputClick(e: React.MouseEvent, toNodeId: string) {
    e.stopPropagation();
    if (!connecting.current || connecting.current.fromId === toNodeId) return;
    // Prevent duplicate edge
    const exists = workflow.edges.find(
      (edge) => edge.from === connecting.current!.fromId && edge.to === toNodeId
    );
    if (!exists) {
      const newEdge: Edge = { id: uid(), from: connecting.current.fromId, to: toNodeId };
      setWorkflow((w) => ({ ...w, edges: [...w.edges, newEdge] }));
    }
    connecting.current = null;
    setTempLine(null);
  }

  function addNode(pluginType: string) {
    const p = getPlugin(pluginType);
    // Place near center of current viewport
    const canvas = canvasRef.current;
    const cx = canvas ? canvas.scrollLeft + canvas.clientWidth / 2 - NW / 2 : 400;
    const cy = canvas ? canvas.scrollTop + canvas.clientHeight / 2 - NH / 2 : 300;
    const newNode: CanvasNode = {
      id: uid(),
      pluginType,
      label: p.label,
      icon: p.icon,
      color: p.color,
      subtitle: p.subtitle,
      x: cx + (Math.random() - 0.5) * 80,
      y: cy + (Math.random() - 0.5) * 80,
    };
    setWorkflow((w) => ({ ...w, nodes: [...w.nodes, newNode] }));
    setSelected(newNode.id);
  }

  function deleteSelected() {
    if (!selected) return;
    setWorkflow((w) => ({
      ...w,
      nodes: w.nodes.filter((n) => n.id !== selected),
      edges: w.edges.filter((e) => e.from !== selected && e.to !== selected),
    }));
    setSelected(null);
  }

  function handleSave() {
    localStorage.setItem(storageKey, JSON.stringify(workflow));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function handleClear() {
    if (confirm("Reset to default workflow?")) {
      const fresh = structuredClone(DEFAULT_WORKFLOWS[agentId]);
      setWorkflow(fresh);
      setSelected(null);
      localStorage.removeItem(storageKey);
    }
  }

  // Delete key shortcut
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.key === "Delete" || e.key === "Backspace") && selected) {
        const active = document.activeElement;
        if (active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA")) return;
        deleteSelected();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected, workflow]); // eslint-disable-line react-hooks/exhaustive-deps

  const nodeById = useCallback(
    (id: string) => workflow.nodes.find((n) => n.id === id),
    [workflow.nodes]
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#0d0d17", overflow: "hidden" }}>
      <TopBar
        name={workflow.name}
        active={workflow.active}
        nodeCount={workflow.nodes.length}
        onNameChange={(v) => setWorkflow((w) => ({ ...w, name: v }))}
        onToggleActive={() => setWorkflow((w) => ({ ...w, active: !w.active }))}
        onSave={handleSave}
        onClear={handleClear}
        saved={saved}
      />

      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        {/* Canvas area */}
        <div
          ref={canvasRef}
          style={{
            flex: 1,
            position: "relative",
            overflow: "auto",
            background: "#0d0d17",
            backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
            cursor: connecting.current ? "crosshair" : "default",
          }}
          onClick={handleCanvasClick}
          onMouseMove={handleCanvasMouseMove}
        >
          {/* Inner large workspace */}
          <div style={{ width: CANVAS_W, height: CANVAS_H, position: "relative" }}>
            {/* SVG connections layer */}
            <svg
              style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none", overflow: "visible" }}
            >
              <defs>
                <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="6" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#4a4a6a" />
                </marker>
              </defs>

              {/* Permanent connections */}
              {workflow.edges.map((edge) => {
                const from = nodeById(edge.from);
                const to = nodeById(edge.to);
                if (!from || !to) return null;
                const op = outputPt(from);
                const ip = inputPt(to);
                return (
                  <path
                    key={edge.id}
                    d={bezier(op.x, op.y, ip.x, ip.y)}
                    fill="none"
                    stroke="#4a4a6a"
                    strokeWidth="2"
                    markerEnd="url(#arrowhead)"
                  />
                );
              })}

              {/* Temp connection line while drawing */}
              {tempLine && (
                <path
                  d={bezier(tempLine.x1, tempLine.y1, tempLine.x2, tempLine.y2)}
                  fill="none"
                  stroke="#F76C45"
                  strokeWidth="2"
                  strokeDasharray="6 3"
                />
              )}
            </svg>

            {/* Node boxes */}
            {workflow.nodes.map((node) => {
              const plugin = getPlugin(node.pluginType);
              return (
                <NodeBox
                  key={node.id}
                  node={node}
                  selected={selected === node.id}
                  plugin={plugin}
                  onPointerDown={(e) => handleNodePointerDown(e, node.id)}
                  onOutputClick={(e) => handleOutputClick(e, node.id)}
                  onInputClick={(e) => handleInputClick(e, node.id)}
                  onDelete={deleteSelected}
                />
              );
            })}

            {/* Empty hint */}
            {workflow.nodes.length === 0 && (
              <div
                style={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                  textAlign: "center",
                  pointerEvents: "none",
                }}
              >
                <p style={{ color: "#4a4a6a", fontSize: 40 }}>+</p>
                <p style={{ color: "#4a4a6a", fontSize: 13 }}>Click a plugin in the panel →<br />to add your first node</p>
              </div>
            )}
          </div>
        </div>

        {/* Right catalog panel */}
        <CatalogPanel search={search} onSearch={setSearch} onAdd={addNode} />
      </div>

      {/* Bottom hint bar */}
      <div
        style={{
          height: 28,
          flexShrink: 0,
          background: "#13131c",
          borderTop: "1px solid #2d2d45",
          display: "flex",
          alignItems: "center",
          padding: "0 16px",
          gap: 20,
        }}
      >
        {[
          "Drag nodes to move",
          "Click ● output port → Click ● input port to connect",
          "Select node + Delete key to remove",
        ].map((hint) => (
          <span key={hint} style={{ color: "#4a4a6a", fontSize: 10 }}>
            {hint}
          </span>
        ))}
      </div>
    </div>
  );
}
