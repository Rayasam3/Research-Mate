import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import ForceGraph2D from "react-force-graph-2d";

import Loading from "./Loading";

// One colour and size per node type. The same types exist in the Neo4j console.
const TYPES = {
  Paper: { color: "#4f46e5", size: 9, label: "Paper" },
  ProposedMethod: { color: "#d946ef", size: 8, label: "Proposed method" },
  Method: { color: "#86efac", size: 4, label: "Baseline / other method" },
  Dataset: { color: "#f59e0b", size: 6, label: "Dataset" },
  Domain: { color: "#a855f7", size: 8, label: "Domain" },
  Task: { color: "#14b8a6", size: 6, label: "Task" },
  Gap: { color: "#ef4444", size: 7, label: "Gap" },
};

// Is dark mode on? (the page adds the class "dark" to <html>)
function useIsDark() {
  return useSyncExternalStore(
    (notify) => {
      const observer = new MutationObserver(notify);
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
      return () => observer.disconnect();
    },
    () => document.documentElement.classList.contains("dark")
  );
}

// A method the paper itself proposes is drawn differently from baselines and other methods.
function kindOf(node) {
  return node.type === "Method" && node.role === "proposed" ? "ProposedMethod" : node.type;
}

function shorten(text, max) {
  if (!text) return "";
  return text.length > max ? text.slice(0, max - 1) + "…" : text;
}

export default function GraphPanel({ state }) {
  const dark = useIsDark();
  const boxRef = useRef(null);
  const graphRef = useRef(null);
  const [width, setWidth] = useState(800);
  const [hidden, setHidden] = useState(["Domain", "Task"]);
  const [selected, setSelected] = useState(null);

  // Keep the canvas as wide as its box.
  useEffect(() => {
    if (!boxRef.current) return undefined;
    const observer = new ResizeObserver((entries) => setWidth(entries[0].contentRect.width));
    observer.observe(boxRef.current);
    return () => observer.disconnect();
  });

  // The graph library changes the objects it gets, so give it copies.
  const graphData = useMemo(() => {
    if (state.status !== "done") return { nodes: [], links: [] };
    const nodes = state.data.nodes.filter((n) => !hidden.includes(kindOf(n))).map((n) => ({ ...n }));
    const ids = new Set(nodes.map((n) => n.id));
    const links = state.data.links
      .filter((l) => ids.has(l.source) && ids.has(l.target))
      .map((l) => ({ ...l }));
    return { nodes, links };
  }, [state, hidden]);

  if (state.status === "loading" || state.status === "idle") return <Loading label="Drawing the knowledge graph..." />;
  if (state.status === "error") return <p className="py-10 text-center text-red-600">Could not load the graph.</p>;
  if (state.data.nodes.length === 0) {
    return <p className="py-10 text-center text-slate-400">The knowledge graph is empty. Wait until the papers are summarized.</p>;
  }

  function toggle(type) {
    setHidden((h) => (h.includes(type) ? h.filter((t) => t !== type) : [...h, type]));
  }

  function drawNode(node, ctx, scale) {
    const kind = kindOf(node);
    const type = TYPES[kind] || TYPES.Method;
    ctx.beginPath();
    ctx.arc(node.x, node.y, type.size, 0, 2 * Math.PI);
    ctx.fillStyle = type.color;
    ctx.fill();
    if (selected && selected.id === node.id) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = dark ? "#fff" : "#0f172a";
      ctx.stroke();
    }
    // Labels: always for papers and proposed methods, only when zoomed in for the rest.
    if (node.type === "Gap") return;
    const important = node.type === "Paper" || kind === "ProposedMethod";
    if (important || scale > 1.4) {
      const text = shorten(node.name, node.type === "Paper" ? 32 : 24);
      ctx.font = `${important ? 4.5 : 3.5}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.fillStyle = dark ? "#e2e8f0" : "#1e293b";
      ctx.fillText(text, node.x, node.y + type.size + 5);
    }
  }

  function linkColor(link) {
    if (link.type === "TESTED_ON") return "#10b981";
    if (link.type.startsWith("ABOUT_")) return "#ef4444";
    return dark ? "#475569" : "#cbd5e1";
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_18rem]">
      <div>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {Object.entries(TYPES).map(([type, info]) => (
            <button
              key={type}
              onClick={() => toggle(type)}
              className={`chip border transition ${
                hidden.includes(type)
                  ? "border-slate-200 bg-transparent text-slate-400 line-through dark:border-slate-700"
                  : "border-transparent bg-white text-slate-700 shadow-sm dark:bg-slate-800 dark:text-slate-200"
              }`}
            >
              <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full" style={{ background: info.color }} />
              {info.label}
            </button>
          ))}
        </div>

        <div ref={boxRef} className="card overflow-hidden">
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            width={width}
            height={520}
            backgroundColor="rgba(0,0,0,0)"
            nodeRelSize={1}
            nodeCanvasObject={drawNode}
            nodePointerAreaPaint={(node, color, ctx) => {
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
              ctx.fill();
            }}
            nodeLabel={(n) => `${n.type}: ${n.name}`}
            linkColor={linkColor}
            linkWidth={(l) => (l.type === "TESTED_ON" ? 2 : 1)}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            onNodeClick={(node) => setSelected(node)}
            cooldownTicks={120}
            onEngineStop={() => graphRef.current && graphRef.current.zoomToFit(400, 40)}
          />
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Drag to move, scroll to zoom, click a node for details. Pink dots are the methods the papers propose; pale
          green dots are baselines they compare against. Green lines are results reported in the papers; red lines
          point to a gap candidate.
        </p>
      </div>

      <aside className="card h-fit p-4 text-sm">
        {selected ? (
          <>
            <span
              className="chip text-white"
              style={{ background: (TYPES[kindOf(selected)] || TYPES.Method).color }}
            >
              {TYPES[kindOf(selected)] ? TYPES[kindOf(selected)].label : selected.type}
            </span>
            <h3 className="mt-2 font-semibold text-slate-900 dark:text-white">
              {selected.type === "Gap" ? "Gap candidate" : selected.name}
            </h3>
            {selected.year && <p className="text-slate-500">{selected.year}</p>}
            {selected.detail && <p className="mt-2 text-slate-600 dark:text-slate-300">{selected.detail}</p>}
            {selected.strength && <p className="mt-2 text-xs text-slate-400">Evidence: {selected.strength}</p>}
          </>
        ) : (
          <p className="text-slate-400">Click a node to see what it is.</p>
        )}
        <hr className="my-4 border-slate-100 dark:border-slate-800" />
        <p className="text-xs text-slate-400">
          {graphData.nodes.length} nodes · {graphData.links.length} links shown. Open the same graph in the Neo4j
          console to explore it further.
        </p>
      </aside>
    </div>
  );
}