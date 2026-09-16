import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { draftRelatedWork, getComparison, getGaps } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import SummaryCard from "../components/SummaryCard";
import { useAgentJob } from "../hooks/useAgentJob";

const TABS = [
  { key: "summaries", label: "Summaries" },
  { key: "compare", label: "Compare" },
  { key: "explore", label: "Explore Deeper" },
];

export default function ResultsPage() {
  const { jobId } = useParams();
  const { status, error } = useAgentJob(jobId);
  const [tab, setTab] = useState("summaries");

  const [comparison, setComparison] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [draft, setDraft] = useState(null);
  const [exploreLoading, setExploreLoading] = useState(false);

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center text-red-600 dark:text-red-400">{error}</div>
    );
  }

  if (!status || status.status === "queued" || status.status === "running") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <LoadingSpinner
          label={
            status && status.status === "running"
              ? "Reading and summarizing real papers - this can take a minute..."
              : "Queued - starting shortly..."
          }
        />
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
  const paperIds = Object.keys(result.summary_results);

  if (result.selected_papers.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <p className="text-lg text-slate-600 dark:text-slate-300">No papers found for "{result.topic}".</p>
        <p className="mt-2 text-sm text-slate-400 dark:text-slate-500">
          Try a broader topic or a different year range.
        </p>
        <Link to="/" className="mt-6 inline-block text-sm font-medium text-brand-600 hover:underline dark:text-brand-400">
          Try another search
        </Link>
      </div>
    );
  }

  function findPaperFor(paperId) {
    return result.selected_papers.find((p) => paperId.endsWith(p.external_id.replace("/", "_")));
  }

  async function loadExploreData() {
    setExploreLoading(true);
    try {
      const [cmp, gap, dr] = await Promise.all([
        getComparison(paperIds),
        getGaps(paperIds),
        draftRelatedWork(paperIds),
      ]);
      setComparison(cmp);
      setGaps(gap);
      setDraft(dr);
    } finally {
      setExploreLoading(false);
    }
  }

  function handleTabChange(key) {
    setTab(key);
    if (key === "compare" && !comparison) {
      getComparison(paperIds).then(setComparison);
    }
    if (key === "explore" && !gaps) {
      loadExploreData();
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <Link to="/" className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-400">
        New search
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
        Results for "{result.topic}"
      </h1>
      <p className="mt-1 text-sm text-slate-400 dark:text-slate-500">
        {paperIds.length} of {result.selected_papers.length} papers summarized
      </p>

      <div className="mt-6 flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-slate-800">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => handleTabChange(t.key)}
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

      {result.errors.length > 0 && (
        <div className="mt-4 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
          Some papers had issues: {result.errors.join("; ")}
        </div>
      )}

      {tab === "summaries" && (
        <div className="mt-6 space-y-4">
          {paperIds.length === 0 && (
            <p className="py-10 text-center text-slate-400 dark:text-slate-500">
              No papers were successfully summarized for this topic.
            </p>
          )}
          {paperIds.map((paperId) => {
            const paper = findPaperFor(paperId);
            if (!paper) return null;
            return (
              <SummaryCard key={paperId} paper={paper} summary={result.summary_results[paperId]} />
            );
          })}
        </div>
      )}

      {tab === "compare" && (
        <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          {!comparison ? (
            <div className="p-10">
              <LoadingSpinner />
            </div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-400 dark:bg-slate-800/50 dark:text-slate-500">
                <tr>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Year</th>
                  <th className="px-4 py-3">Methods</th>
                  <th className="px-4 py-3">Datasets</th>
                </tr>
              </thead>
              <tbody>
                {comparison.rows.map((row) => (
                  <tr key={row.paper_id} className="border-t border-slate-100 align-top dark:border-slate-800">
                    <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">{row.title}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{row.year || "-"}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                      {row.methods.join(", ") || "-"}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                      {row.datasets.join(", ") || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "explore" && (
        <div className="mt-6 space-y-8">
          {exploreLoading && <LoadingSpinner label="Analyzing gaps and drafting related work..." />}

          {gaps && (gaps.method_gaps.length > 0 || gaps.dataset_gaps.length > 0) && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="font-semibold text-slate-900 dark:text-white">Potential Research Gaps</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-300">
                {[...gaps.method_gaps, ...gaps.dataset_gaps].map((g, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-brand-500 dark:text-brand-400">-</span>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {draft && draft.paragraph && (
            <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <h3 className="font-semibold text-slate-900 dark:text-white">Related Work Draft</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{draft.paragraph}</p>
              {draft.skipped_paper_ids.length > 0 && (
                <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
                  Skipped (not yet summarized): {draft.skipped_paper_ids.join(", ")}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}