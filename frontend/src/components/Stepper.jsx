// Shows which agent step is finished, which one is running, and which are still waiting.
const STEPS = [
  { key: "search", label: "Searching 4 paper sources" },
  { key: "domain", label: "Detecting the research field" },
  { key: "filter", label: "Ranking papers by relevance" },
  { key: "ingest", label: "Downloading and reading the papers" },
  { key: "summarize", label: "Summarizing and building the knowledge graph" },
];

export default function Stepper({ stepsDone = [], failed = false }) {
  const activeIndex = STEPS.findIndex((s) => !stepsDone.includes(s.key));

  return (
    <div className="card mx-auto max-w-xl p-6">
      <h2 className="section-title">Working on it...</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Reading full papers takes a few minutes. You can keep this page open.
      </p>
      <ol className="mt-5 space-y-3">
        {STEPS.map((step, i) => {
          const done = stepsDone.includes(step.key);
          const active = i === activeIndex && !failed;
          return (
            <li key={step.key} className="flex items-center gap-3 text-sm">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  done
                    ? "bg-emerald-500 text-white"
                    : active
                      ? "animate-pulse bg-brand-600 text-white"
                      : "bg-slate-200 text-slate-400 dark:bg-slate-800"
                }`}
              >
                {done ? "✓" : i + 1}
              </span>
              <span
                className={
                  done
                    ? "text-slate-500 dark:text-slate-400"
                    : active
                      ? "font-semibold text-slate-900 dark:text-white"
                      : "text-slate-400 dark:text-slate-600"
                }
              >
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
