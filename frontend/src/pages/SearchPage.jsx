import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { runAgent } from "../api/client";

export default function SearchPage() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState("");
  const [maxPapers, setMaxPapers] = useState(5);
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSearch(e) {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const { job_id } = await runAgent(
        topic.trim(),
        maxPapers,
        yearFrom ? parseInt(yearFrom, 10) : undefined,
        yearTo ? parseInt(yearTo, 10) : undefined
      );
      navigate(`/results/${job_id}`);
    } catch (err) {
      const status = err && err.response ? err.response.status : null;
      if (status === 429) {
        setError("You've hit the rate limit — please try again shortly.");
      } else {
        setError("Something went wrong starting the search. Please try again.");
      }
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-20">
      <div className="text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">
          Research, <span className="text-brand-600">summarized</span>.
        </h1>
        <p className="mx-auto mt-3 max-w-md text-slate-500">
          Give it a topic. It searches real papers, reads them, and hands you
          back plain-English summaries with citations.
        </p>
      </div>

      <form onSubmit={handleSearch} className="mt-10 space-y-4">
        <div className="relative">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. graph neural networks"
            className="w-full rounded-xl border border-slate-300 px-5 py-4 text-base shadow-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>

        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="text-sm font-medium text-slate-500 hover:text-slate-700"
        >
          {showFilters ? "Hide options ▲" : "More options ▼"}
        </button>

        {showFilters && (
          <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">
                Max papers
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={maxPapers}
                onChange={(e) => setMaxPapers(parseInt(e.target.value, 10) || 5)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">
                Year from
              </label>
              <input
                type="number"
                value={yearFrom}
                onChange={(e) => setYearFrom(e.target.value)}
                placeholder="2020"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">
                Year to
              </label>
              <input
                type="number"
                value={yearTo}
                onChange={(e) => setYearTo(e.target.value)}
                placeholder="2025"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-200"
              />
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-brand-600 px-5 py-4 text-base font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Starting research…" : "Research This Topic"}
        </button>
      </form>

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-12 grid grid-cols-3 gap-4 text-center text-xs text-slate-400">
        <div>
          <div className="text-lg font-bold text-slate-700">4</div>
          Sources searched
        </div>
        <div>
          <div className="text-lg font-bold text-slate-700">AI</div>
          Plain-English summaries
        </div>
        <div>
          <div className="text-lg font-bold text-slate-700">Auto</div>
          Citations generated
        </div>
      </div>
    </div>
  );
}