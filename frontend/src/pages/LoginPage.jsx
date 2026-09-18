import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login as loginApi, signup as signupApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = isSignup ? await signupApi(email, password) : await loginApi(email, password);
      login(data.access_token);
      navigate("/");
    } catch (err) {
      const detail = err && err.response && err.response.data ? err.response.data.detail : null;
      setError(detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm px-4 py-20">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
        {isSignup ? "Create an account" : "Log in"}
      </h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {isSignup ? "Start researching in seconds." : "Welcome back."}
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Password</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
          />
        </div>

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? "Please wait..." : isSignup ? "Sign up" : "Log in"}
        </button>
      </form>

      <button
        onClick={() => setIsSignup(!isSignup)}
        className="mt-4 text-sm font-medium text-brand-600 hover:underline dark:text-brand-400"
      >
        {isSignup ? "Already have an account? Log in" : "No account? Sign up"}
      </button>
    </div>
  );
}