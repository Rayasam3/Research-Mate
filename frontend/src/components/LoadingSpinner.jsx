export default function LoadingSpinner({ label }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-brand-100 border-t-brand-600" />
      {label && <p className="mt-4 text-slate-500">{label}</p>}
    </div>
  );
}