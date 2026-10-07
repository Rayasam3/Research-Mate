import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { draftRelatedWork, getComparison, getGaps, getGraphView } from "../api/client";
import ComparePanel from "../components/ComparePanel";
import GapsPanel from "../components/GapsPanel";
import GraphPanel from "../components/GraphPanel";
import RelatedWorkPanel from "../components/RelatedWorkPanel";
import Stepper from "../components/Stepper";
import SummaryCard from "../components/SummaryCard";
import { useAgentJob } from "../hooks/useAgentJob";

const TABS = [
  { key: "papers", label: "Papers" },
  { key: "compare", label: "Compare" },
  { key: "graph", label: "Knowledge graph" },
  { key: "gaps", label: "Research gaps" },
  { key: "related", label: "Related work" },
];

const IDLE = { status: "idle", data: null };

export default function ResultsPage() {
  const { jobId } = useParams();
  const { status, error } = useAgentJob(jobId);
  const [tab, setTab] = useState("papers");

  // One small state object per tab: { status: idle | loading | done | error, data }
  const [panels, setPanels] = useState({ compare: IDLE, graph: IDLE, gaps: IDLE, related: IDLE });

  async function load(name, fetcher) {
    setPanels((p) => ({ ...p, [name]: { status: "loading", data: null } }));
    try {
      const data = await fetcher();
      setPanels((p) => ({ ...p, [name]: { status: "done", data } }));
    } catch {
      setPanels((p) => ({ ...p, [name]: { status: "error", data: null } }));
    }
  }

  if (error) {
    return <div className="mx-auto max-w-2xl px-4 py-16 text-center text-red-600 dark:text-red-400">{error}</div>;
  }

  if (!status || status.status === "queued" || status.status === "running") {
    return (
      <div className="px-4 py-12">
        <Stepper stepsDone={status ? status.steps_done : []} />
      </div>
    );
  }

  if (status.status === "failed") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-red-600 dark:text-red-400">Something went wrong: {status.error}</p>
        <Link to="/" className="mt-4 inline-block text-brand-600 hover:underline dark:text-brand-400">
          Try another search
        </Link>
      </div>
    );
  }

  const result = status.result;
  const paperIds = Object.keys(result.summary_results || {});
  const selected = result.selected_papers || [];
  const info = result.selection_info || {};

  if (selected.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <p className="text-lg text-slate-600 dark:text-slate-300">No papers found for &quot;{result.topic}&quot;.</p>
        <p className="mt-2 text-sm text-slate-400">
          Try a broader topic or a different year range. If this keeps happening, check your internet connection.
        </p>
        <Link to="/" className="btn-primary mt-6">
          Try another search
        </Link>
      </div>
    );
  }

  function findPaperFor(paperId) {
    return selected.find((p) => paperId === `${p.source}_${p.external_id.replace("/", "_")}`);
  }

  function handleTab(key) {
    setTab(key);
    if (key === "compare" && panels.compare.status === "idle") load("compare", () => getComparison(paperIds));
    if (key === "gaps" && panels.gaps.status === "idle") load("gaps", () => getGaps(paperIds));
    if (key === "graph" && panels.graph.status === "idle") {
      // The gap analysis saves the gap candidates as nodes, so run it first and the graph can show them.
      const gapsFirst =
        panels.gaps.status === "idle" ? load("gaps", () => getGaps(paperIds)) : Promise.resolve();
      gapsFirst.then(() => load("graph", () => getGraphView(paperIds)));
    }
  }

  const fieldCount = info.field_counts && info.detected_field ? info.field_counts[info.detected_field] : null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <Link to="/" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-400">
        ← New search
      </Link>
      <h1 className="mt-2 font-display text-3xl font-semibold text-slate-900 dark:text-white">{result.topic}</h1>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        {info.detected_field && (
          <span className="chip bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
            Field: {info.detected_field}
            {fieldCount != null && ` (${fieldCount} of ${info.considered} papers)`}
          </span>
        )}
        {info.user_field && (
          <span className="chip bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            Your field: {info.user_field}
          </span>
        )}
        <span className="chip bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {paperIds.length} of {selected.length} papers summarized
        </span>
        {info.dropped_off_topic > 0 && (
          <span className="chip bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
            {info.dropped_off_topic} off-topic papers removed
          </span>
        )}
        {info.dropped_other_field > 0 && (
          <span className="chip bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
            {info.dropped_other_field} papers from other fields removed
          </span>
        )}
      </div>

      <div className="mt-6 flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-slate-800">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => handleTab(t.key)}
            className={`whitespace-nowrap px-4 py-2.5 text-sm font-medium transition ${
              tab === t.key
                ? "border-b-2 border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {result.skipped_papers && result.skipped_papers.length > 0 && (
        <details className="mt-4 rounded-lg bg-slate-100 px-4 py-3 text-sm text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
          <summary className="cursor-pointer font-medium">
            {result.skipped_papers.length} paper(s) could not be read and were replaced by the next best paper
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {result.skipped_papers.map((s, i) => (
              <li key={i}>
                <span className="font-medium">{s.title}</span>: {s.reason}
              </li>
            ))}
          </ul>
        </details>
      )}

      {paperIds.length < (result.max_papers || 0) && (
        <div className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
          You asked for {result.max_papers} papers but only {paperIds.length} readable open-access papers were found for
          this topic. Try a broader topic or a wider year range.
        </div>
      )}

      {result.errors && result.errors.length > 0 && (
        <div className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
          Some papers had issues: {result.errors.join("; ")}
        </div>
      )}

      <div className="mt-6">
        {tab === "papers" && (
          <div className="grid gap-4 lg:grid-cols-2">
            {paperIds.length === 0 && (
              <p className="py-10 text-center text-slate-400 lg:col-span-2">
                No papers were summarized for this topic.
              </p>
            )}
            {paperIds.map((paperId) => {
              const paper = findPaperFor(paperId);
              if (!paper) return null;
              return <SummaryCard key={paperId} paper={paper} summary={result.summary_results[paperId]} />;
            })}
          </div>
        )}
        {tab === "compare" && <ComparePanel state={panels.compare} />}
        {tab === "graph" && <GraphPanel state={panels.graph} />}
        {tab === "gaps" && <GapsPanel state={panels.gaps} />}
        {tab === "related" && (
          <RelatedWorkPanel state={panels.related} onGenerate={() => load("related", () => draftRelatedWork(paperIds))} />
        )}
      </div>
    </div>
  );
}
