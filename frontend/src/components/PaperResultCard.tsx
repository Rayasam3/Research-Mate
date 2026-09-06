import type { Paper } from "../api/client";

const SOURCE_LABELS: Record<Paper["source"], string> = {
  arxiv: "ArXiv",
  semantic_scholar: "Semantic Scholar",
  pubmed: "PubMed",
};

export default function PaperResultCard({ paper }: { paper: Paper }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-slate-900">{paper.title}</h3>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
          {SOURCE_LABELS[paper.source]}
        </span>
      </div>

      {paper.authors.length > 0 && (
        <p className="mt-1 text-sm text-slate-500">{paper.authors.join(", ")}</p>
      )}

      {paper.abstract && (
        <p className="mt-2 line-clamp-3 text-sm text-slate-700">{paper.abstract}</p>
      )}

      <div className="mt-3 flex gap-4 text-sm">
        {paper.pdf_url && (
          <a
            href={paper.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-blue-600 hover:underline"
          >
            PDF
          </a>
        )}
        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-blue-600 hover:underline"
          >
            View source
          </a>
        )}
      </div>
    </div>
  );
}
