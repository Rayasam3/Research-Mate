import { Link } from "react-router-dom";

export default function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link to="/" className="flex items-center gap-2">
          <span className="text-2xl">📄</span>
          <span className="text-lg font-bold text-slate-900">Research Mate</span>
        </Link>
        <span className="text-sm text-slate-400">AI Research Assistant</span>
      </div>
    </header>
  );
}