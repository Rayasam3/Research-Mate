import { useState } from "react";

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      onClick={handleCopy}
      className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
    >
      {copied ? "Copied" : label}
    </button>
  );
}

const SOURCE_LABELS = {
  arxiv: "ArXiv",
  semantic_scholar: "Semantic Scholar",
  pubmed: "PubMed",
  openalex: "OpenAlex",
};

export default function SummaryCard({ paper, summary }) {
  const [expanded, setExpanded] = useState(false);

  if (!summary || !summary.card) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
        <h3 className="font-semibold text-slate-900">{paper.title}</h3>
        <p className="mt-1 text-sm text-amber-700">
          {summary && summary.message ? summary.message : "Could not summarize this paper."}
        </p>
      </div>
    );
  }

  const card = summary.card;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-lg font-semibold leading-snug text-slate-900">{paper.title}</h3>
          <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500">
            {SOURCE_LABELS[paper.source] || paper.source}
          </span>
        </div>
        <p className="mt-1.5 text-sm text-slate-500">
          {paper.authors.slice(0, 4).join(", ")}
          {paper.authors.length > 4 ? ", et al." : ""}
        </p>

        <div className="mt-4 rounded-lg bg-brand-50 p-4 text-sm leading-relaxed text-brand-900">
          {card.tldr}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          {expanded ? "Show less" : "Show full details"}
        </button>

        {expanded && (
          <div className="mt-4 space-y-4 border-t border-slate-100 pt-4 text-sm leading-relaxed text-slate-700">
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Problem
              </h4>
              <p>{card.problem}</p>
            </div>
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Method
              </h4>
              <p>{card.method_explained}</p>
            </div>
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Key Results
              </h4>
              <p>{card.key_results}</p>
            </div>
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Limitations
              </h4>
              <p>{card.limitations}</p>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 border-t border-slate-100 bg-slate-50 px-5 py-3">
        <CopyButton text={card.citation_apa} label="Copy APA" />
        <CopyButton text={card.citation_bibtex} label="Copy BibTeX" />
                {paper.pdf_url && (<a href={paper.pdf_url} target="_blank" rel="noreferrer" className="ml-auto text-xs font-medium text-brand-600 hover:underline">View PDF</a>)}
      </div>
    </div>
  );
}