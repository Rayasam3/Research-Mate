import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { runAgent } from "../api/client";

// Same list as the backend (app/services/domain.py -> FIELDS).
const FIELDS = [
  "Computer Science",
  "Medicine & Health",
  "Biology & Life Sciences",
  "Physics",
  "Mathematics & Statistics",
  "Engineering",
  "Chemistry & Materials",
  "Economics & Business",
  "Social Sciences & Humanities",
  "Environmental & Earth Science",
];

const EXAMPLES = ["graph neural networks", "federated learning", "ECG arrhythmia detection", "CRISPR gene editing"];

const STEPS = [
  ["1", "Search", "ArXiv, Semantic Scholar, PubMed and OpenAlex"],
  ["2", "Find the field", "Detects the research field and drops off-topic papers"],
  ["3", "Read the full paper", "Methods, datasets, results, limitations, future work"],
  ["4", "Build the graph", "Knowledge graph in Neo4j, with gap candidates and evidence"],
];

// Remember the user's field between visits.
function savedField() {
  try {
    return localStorage.getItem("rm_field") || "";
  } catch {
    return "";
  }
}

export default function SearchPage() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState("");
  const [field, setField] = useState(savedField);
  const [maxPapers, setMaxPapers] = useState(5);
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function changeField(value) {
    setField(value);
    try {
      localStorage.setItem("rm_field", value);
    } catch {
      // storage not available: the field is simply not remembered
    }
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const { job_id } = await runAgent({
        topic: topic.trim(),
        maxPapers,
        yearFrom: yearFrom ? parseInt(yearFrom, 10) : undefined,
        yearTo: yearTo ? parseInt(yearTo, 10) : undefined,
        field,
      });
      navigate(`/results/${job_id}`);
    } catch (err) {
      const status = err && err.response ? err.response.status : null;
      setError(
        status === 429
          ? "You've hit the rate limit. Please try again shortly."
          : "Could not start the search. Is the backend running?"
      );
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-14">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="font-display text-5xl font-semibold leading-tight tracking-tight text-slate-900 dark:text-white">
          Find what is <span className="text-brand-600 dark:text-brand-400">still unexplored</span>.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-slate-500 dark:text-slate-400">
          Give a topic. Research Mate reads the full papers in your field and shows how methods, datasets and
          results connect, and where the evidence points to a gap.
        </p>
      </div>

      <form onSubmit={handleSearch} className="card mx-auto mt-10 max-w-2xl space-y-4 p-5">
        <div>
          <label className="field-label">Research topic</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. graph neural networks"
            className="field-input !py-3 !text-base"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                type="button"
                key={ex}
                onClick={() => setTopic(ex)}
                className="chip bg-slate-100 text-slate-600 hover:bg-brand-50 hover:text-brand-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-4">
          <div className="sm:col-span-2">
            <label className="field-label">Your field of study</label>
            <select value={field} onChange={(e) => changeField(e.target.value)} className="field-input">
              <option value="">Auto-detect from the topic</option>
              {FIELDS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Papers (1-10)</label>
            <input
              type="number"
              min={1}
              max={10}
              value={maxPapers}
              onChange={(e) => setMaxPapers(parseInt(e.target.value, 10) || 5)}
              className="field-input"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="field-label">From</label>
              <input
                type="number"
                value={yearFrom}
                onChange={(e) => setYearFrom(e.target.value)}
                placeholder="2020"
                className="field-input"
              />
            </div>
            <div>
              <label className="field-label">To</label>
              <input
                type="number"
                value={yearTo}
                onChange={(e) => setYearTo(e.target.value)}
                placeholder="2026"
                className="field-input"
              />
            </div>
          </div>
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full !py-3.5 !text-base">
          {loading ? "Starting..." : "Research this topic"}
        </button>

        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-400">
            {error}
          </div>
        )}
      </form>

      <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map(([num, title, text]) => (
          <div key={num} className="card p-5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-sm font-bold text-brand-700 dark:bg-brand-950 dark:text-brand-300">
              {num}
            </div>
            <h3 className="mt-3 font-semibold text-slate-900 dark:text-white">{title}</h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
