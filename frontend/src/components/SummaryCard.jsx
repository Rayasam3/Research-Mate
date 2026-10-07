import { useState } from "react";

const SOURCE_LABELS = {
  arxiv: "ArXiv",
  semantic_scholar: "Semantic Scholar",
  pubmed: "PubMed",
  openalex: "OpenAlex",
};

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button onClick={handleCopy} className="btn-ghost !px-3 !py-1 !text-xs">
      {copied ? "Copied" : label}
    </button>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
        {title}
      </h4>
      <p>{children}</p>
    </div>
  );
}

export default function SummaryCard({ paper, summary }) {
  const [expanded, setExpanded] = useState(false);
  const year = paper.published_date ? paper.published_date.slice(0, 4) : null;

  if (!summary || !summary.card) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 dark:border-amber-900 dark:bg-amber-950/40">
        <h3 className="font-semibold text-slate-900 dark:text-white">{paper.title}</h3>
        <p className="mt-1 text-sm text-amber-700 dark:text-amber-400">
          {summary && summary.message ? summary.message : "Could not summarize this paper."}
        </p>
      </div>
    );
  }

  const card = summary.card;

  return (
    <article className="card overflow-hidden">
      <div className="p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {SOURCE_LABELS[paper.source] || paper.source}
          </span>
          {paper.field && (
            <span className="chip bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300">{paper.field}</span>
          )}
          {year && <span className="chip bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">{year}</span>}
          {paper.citation_count != null && (
            <span className="chip bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
              {paper.citation_count} citations
            </span>
          )}
        </div>

        <h3 className="mt-3 font-display text-xl font-semibold leading-snug text-slate-900 dark:text-white">
          {paper.title}
        </h3>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {paper.authors.slice(0, 4).join(", ")}
          {paper.authors.length > 4 ? ", et al." : ""}
        </p>

        <div className="mt-4 rounded-xl bg-brand-50 p-4 text-sm leading-relaxed text-brand-900 dark:bg-brand-950/50 dark:text-brand-100">
          {card.tldr}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 text-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
        >
          {expanded ? "Show less" : "Show full details"}
        </button>

        {expanded && (
          <div className="mt-4 space-y-4 border-t border-slate-100 pt-4 text-sm leading-relaxed text-slate-700 dark:border-slate-800 dark:text-slate-300">
            {card.abstract && <Section title="Abstract (from the paper)">{card.abstract}</Section>}
            <Section title="Problem">{card.problem}</Section>
            <Section title="Method">{card.method_explained}</Section>
            <Section title="Key results">{card.key_results}</Section>
            <Section title="Limitations">{card.limitations}</Section>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 bg-slate-50 px-5 py-3 dark:border-slate-800 dark:bg-slate-800/40">
        <CopyButton text={card.citation_apa} label="Copy APA" />
        <CopyButton text={card.citation_bibtex} label="Copy BibTeX" />
        {paper.pdf_url && (
          <a
            href={paper.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="ml-auto text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
          >
            View PDF
          </a>
        )}
      </div>
    </article>
  );
}
