import { useState } from "react";

import { type Paper, searchPapers } from "../api/client";
import PaperResultCard from "../components/PaperResultCard";

export default function SearchPage() {
  const [topic, setTopic] = useState("");
  const [results, setResults] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await searchPapers(topic.trim());
      setResults(data.results);
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 429) {
        setError("You've hit the search limit — please try again in a bit.");
      } else {
        setError("Something went wrong while searching. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-bold text-slate-900">📄 Research Mate</h1>
      <p className="mt-1 text-slate-500">
        Search ArXiv, Semantic Scholar, and PubMed for papers on any topic.
      </p>

      <form onSubmit={handleSearch} className="mt-6 flex gap-2">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. transformer attention mechanisms"
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <div className="mt-6 space-y-3">
        {results.length === 0 && !loading && !error && (
          <p className="text-sm text-slate-400">No results yet — try a search above.</p>
        )}
        {results.map((paper) => (
          <PaperResultCard key={`${paper.source}-${paper.external_id}`} paper={paper} />
        ))}
      </div>
    </div>
  );
}
