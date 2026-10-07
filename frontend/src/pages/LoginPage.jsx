import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login as loginApi, signup as signupApi } from "../api/client";
import { useAuth } from "../context/useAuth";

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
      setError(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl items-center gap-10 px-4 py-16 md:grid-cols-2">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
          Agentic literature analyst
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold leading-tight text-slate-900 dark:text-white">
          Read the papers. <br />
          See the <span className="text-brand-600 dark:text-brand-400">gaps</span>.
        </h1>
        <p className="mt-4 max-w-md text-slate-500 dark:text-slate-400">
          Research Mate reads full papers, builds a knowledge graph of methods, datasets and results, and shows
          evidence-backed research-gap candidates.
        </p>
      </div>

      <div className="card p-6">
        <h2 className="section-title">{isSignup ? "Create an account" : "Log in"}</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {isSignup ? "Start researching in seconds." : "Welcome back."}
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="field-label">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field-input"
            />
          </div>
          <div>
            <label className="field-label">Password (min 8 characters)</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field-input"
            />
          </div>

          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary w-full">
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
    </div>
  );
}
