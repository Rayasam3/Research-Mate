export default function LoadingSpinner({ label }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-brand-100 border-t-brand-600 dark:border-slate-800 dark:border-t-brand-500" />
      {label && <p className="mt-4 text-slate-500 dark:text-slate-400">{label}</p>}
    </div>
  );
}