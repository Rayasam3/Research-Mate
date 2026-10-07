import { useState } from "react";

import Loading from "./Loading";

export default function RelatedWorkPanel({ state, onGenerate }) {
  const [copied, setCopied] = useState(false);

  async function copy(text) {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (state.status === "idle") {
    return (
      <div className="card mx-auto max-w-xl p-8 text-center">
        <h2 className="section-title">Related Work draft</h2>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Writes one paragraph that connects the summarized papers, with citations and a BibTeX list.
        </p>
        <button onClick={onGenerate} className="btn-primary mt-5">
          Generate draft
        </button>
      </div>
    );
  }
  if (state.status === "loading") return <Loading label="Writing the draft..." />;
  if (state.status === "error") return <p className="py-10 text-center text-red-600">Could not write the draft.</p>;

  const draft = state.data;
  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <h2 className="section-title">Related Work draft</h2>
          <button onClick={() => copy(draft.paragraph)} className="btn-ghost !text-xs">
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{draft.paragraph}</p>
        {draft.skipped_paper_ids.length > 0 && (
          <p className="mt-3 text-xs text-slate-400">Skipped (not summarized): {draft.skipped_paper_ids.join(", ")}</p>
        )}
      </div>

      {draft.bibtex_references.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white">BibTeX</h3>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs text-slate-700 dark:bg-slate-950 dark:text-slate-300">
            {draft.bibtex_references.join("\n\n")}
          </pre>
        </div>
      )}
    </div>
  );
}
