export default function Loading({ label = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-100 border-t-brand-600 dark:border-slate-800 dark:border-t-brand-500" />
      <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">{label}</p>
    </div>
  );
}
