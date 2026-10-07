import { useState } from "react";

import Loading from "./Loading";

const SHOW_METHODS = 4;
const SHOW_DATASETS = 5;

// The paper's main proposed method: the proposed method whose name appears in the
// title (MECCH, DAGNN...), otherwise the first proposed one. Surveys have none.
function mainMethod(row) {
  const proposed = row.methods.filter((m) => m.role === "proposed");
  if (proposed.length === 0) return null;
  const title = row.title.toLowerCase();
  return proposed.find((m) => title.includes(m.name.toLowerCase())) || proposed[0];
}

// Shows the first few items as chips and "+N more" for the rest.
function ChipList({ items, limit, className }) {
  if (items.length === 0) return <span className="text-slate-400">—</span>;
  const shown = items.slice(0, limit);
  const rest = items.length - shown.length;
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((item) => (
        <span key={item} className={`chip ${className}`}>
          {item}
        </span>
      ))}
      {rest > 0 && <span className="self-center text-xs text-slate-400">+{rest} more</span>}
    </div>
  );
}

function TableView({ rows }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[56rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800">
            <th className="px-4 py-3 font-semibold">Paper</th>
            <th className="px-4 py-3 font-semibold">Task</th>
            <th className="px-4 py-3 font-semibold">Proposed method</th>
            <th className="px-4 py-3 font-semibold">Compared against</th>
            <th className="px-4 py-3 font-semibold">Datasets</th>
            <th className="px-4 py-3 text-center font-semibold">Limitations</th>
            <th className="px-4 py-3 text-center font-semibold">Future work</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {rows.map((row) => {
            const main = mainMethod(row);
            const baselines = row.methods
              .filter((m) => m.role !== "proposed" || (main && m.name !== main.name))
              .map((m) => m.name);
            return (
              <tr key={row.paper_id} className="align-top">
                <td className="max-w-[15rem] px-4 py-4">
                  <p className="font-semibold leading-snug text-slate-900 dark:text-white">{row.title}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {[row.year, row.domain].filter(Boolean).join(" · ")}
                  </p>
                </td>
                <td className="max-w-[12rem] px-4 py-4 text-slate-600 dark:text-slate-300">{row.task || "—"}</td>
                <td className="max-w-[14rem] px-4 py-4">
                  {main ? (
                    <>
                      <span className="chip bg-fuchsia-100 font-semibold text-fuchsia-700 dark:bg-fuchsia-950/60 dark:text-fuchsia-300">
                        {main.name}
                      </span>
                      {main.novelty && (
                        <p className="mt-1.5 text-xs leading-snug text-slate-500 dark:text-slate-400">{main.novelty}</p>
                      )}
                    </>
                  ) : (
                    <span className="text-xs text-slate-400">None (survey or analysis paper)</span>
                  )}
                </td>
                <td className="max-w-[16rem] px-4 py-4">
                  <ChipList
                    items={baselines}
                    limit={SHOW_METHODS}
                    className="bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
                  />
                </td>
                <td className="max-w-[16rem] px-4 py-4">
                  <ChipList
                    items={row.datasets}
                    limit={SHOW_DATASETS}
                    className="bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
                  />
                </td>
                <td className="px-4 py-4 text-center text-slate-600 dark:text-slate-300">{row.n_limitations}</td>
                <td className="px-4 py-4 text-center text-slate-600 dark:text-slate-300">{row.n_future_work}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CardsView({ rows }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {rows.map((row) => (
        <article key={row.paper_id} className="card p-5">
          <div className="flex flex-wrap gap-2">
            {row.domain && (
              <span className="chip bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300">{row.domain}</span>
            )}
            {row.year && <span className="chip bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">{row.year}</span>}
          </div>
          <h3 className="mt-2 font-display text-lg font-semibold leading-snug text-slate-900 dark:text-white">
            {row.title}
          </h3>
          {row.task && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Task: {row.task}</p>}

          <h4 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">Methods</h4>
          <ul className="space-y-2">
            {row.methods.length === 0 && <li className="text-sm text-slate-400">None found</li>}
            {row.methods.map((m) => (
              <li key={m.name} className="text-sm">
                <span
                  className={`chip ${
                    m.shared
                      ? "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
                  }`}
                >
                  {m.name}
                </span>
                {m.role === "proposed" && (
                  <span className="ml-2 text-xs font-semibold text-fuchsia-600 dark:text-fuchsia-400">proposed</span>
                )}
                {m.novelty && <p className="mt-1 text-slate-500 dark:text-slate-400">New: {m.novelty}</p>}
              </li>
            ))}
          </ul>

          <h4 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">Datasets</h4>
          <div className="flex flex-wrap gap-2">
            {row.datasets.length === 0 && <span className="text-sm text-slate-400">None found</span>}
            {row.datasets.map((d) => (
              <span key={d} className="chip bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
                {d}
              </span>
            ))}
          </div>

          <p className="mt-4 text-xs text-slate-400">
            {row.n_limitations} limitations and {row.n_future_work} future-work statements by the authors
          </p>
        </article>
      ))}
    </div>
  );
}

// Compare tab: a table (one row per paper) for a quick side-by-side view, and the
// detailed cards (every method and dataset) one click away.
export default function ComparePanel({ state }) {
  const [view, setView] = useState("table");

  if (state.status === "loading" || state.status === "idle") return <Loading label="Reading the knowledge graph..." />;
  if (state.status === "error") return <p className="py-10 text-center text-red-600">Could not load the comparison.</p>;

  const rows = state.data.rows;
  if (rows.length === 0) {
    return (
      <p className="py-10 text-center text-slate-400">
        These papers are not in the knowledge graph yet. Wait until the summaries are finished.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Each paper has its own method, so compare what is <b>different</b>: the proposed method, the methods it is
          compared against, and the datasets it is tested on.
        </p>
        <div className="inline-flex rounded-lg border border-slate-200 p-0.5 text-sm dark:border-slate-700">
          {[
            ["table", "Table"],
            ["cards", "Cards (full lists)"],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setView(key)}
              className={`rounded-md px-3 py-1 transition ${
                view === key
                  ? "bg-brand-600 text-white"
                  : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {view === "table" ? <TableView rows={rows} /> : <CardsView rows={rows} />}

      {view === "table" && (
        <p className="text-xs text-slate-400">
          Only the first {SHOW_METHODS} compared methods and {SHOW_DATASETS} datasets are shown per paper. Open
          &quot;Cards&quot; to see the full lists. Limitations and future work are the counts of statements written by
          the authors.
        </p>
      )}
    </div>
  );
}