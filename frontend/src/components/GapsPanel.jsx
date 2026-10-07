import Loading from "./Loading";

const STRENGTH_STYLE = {
  strong: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300",
  moderate: "bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300",
  weak: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};

function EvidenceList({ title, items }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</p>
      <ul className="mt-1 space-y-0.5 text-sm text-slate-600 dark:text-slate-300">
        {items.map((e) => (
          <li key={e.title}>
            {e.title} {e.year && <span className="text-slate-400">({e.year})</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Statements({ title, items, emptyText }) {
  return (
    <div className="card p-5">
      <h3 className="section-title !text-lg">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">{emptyText}</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {items.map((item, i) => (
            <li key={i} className="text-sm">
              <p className="text-slate-700 dark:text-slate-200">&ldquo;{item.text}&rdquo;</p>
              <p className="mt-0.5 text-xs text-slate-400">
                {item.paper_title} {item.year && `(${item.year})`}
                {item.citations != null && ` · ${item.citations} citations`}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function GapsPanel({ state }) {
  if (state.status === "loading" || state.status === "idle") return <Loading label="Looking for gap candidates..." />;
  if (state.status === "error") return <p className="py-10 text-center text-red-600">Could not load the gap analysis.</p>;

  const { untested_combinations: combos, future_work: futureWork, limitations, summary } = state.data;

  return (
    <div className="space-y-8">
      <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900 dark:border-brand-900 dark:bg-brand-950/40 dark:text-brand-100">
        <strong>How to read this:</strong> a candidate gap is a lead with evidence, not a proven gap. A method
        being rare does not make it a gap (it may be outdated). So gaps here come from two kinds of evidence:
        combinations nobody has tried, and what the authors wrote themselves.
        <p className="mt-2 text-xs opacity-80">
          Looked at {summary.papers} papers, {summary.core_methods} core methods and {summary.datasets} datasets.{" "}
          {summary.pairs_not_tested} method–dataset pairs were never tried together.
        </p>
      </div>

      <section>
        <h2 className="section-title">Untested combinations</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          A core method and a dataset that other papers use, but that no paper combined.
        </p>
        {combos.length === 0 ? (
          <p className="mt-4 text-sm text-slate-400">
            No untested combinations found in this set of papers. Try more papers or a broader topic.
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {combos.map((c, i) => (
              <article key={i} className="card p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`chip ${STRENGTH_STYLE[c.strength]}`}>{c.strength} evidence</span>
                  <span className="chip bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
                    {c.method}
                  </span>
                  <span className="text-slate-400">×</span>
                  <span className="chip bg-amber-50 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
                    {c.dataset}
                  </span>
                  <span className="ml-auto text-xs text-slate-400">score {c.score}</span>
                </div>
                <p className="mt-3 text-slate-800 dark:text-slate-100">{c.statement}</p>

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <EvidenceList title="Method comes from" items={c.method_evidence} />
                  <EvidenceList title="Dataset comes from" items={c.dataset_evidence} />
                </div>

                {c.author_hint && (
                  <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
                    <strong>The authors point at this:</strong> &ldquo;{c.author_hint.text}&rdquo;
                    <span className="block text-xs opacity-70">{c.author_hint.paper_title}</span>
                  </p>
                )}
                {c.caveats.length > 0 && (
                  <ul className="mt-3 space-y-1 text-xs text-amber-700 dark:text-amber-400">
                    {c.caveats.map((cv) => (
                      <li key={cv}>⚠ {cv}</li>
                    ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="section-title">Stated by the authors</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Taken from the full text of each paper, newest first.
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Statements title="Future work" items={futureWork} emptyText="No future-work statements were found." />
          <Statements title="Limitations" items={limitations} emptyText="No limitations were found." />
        </div>
      </section>
    </div>
  );
}
