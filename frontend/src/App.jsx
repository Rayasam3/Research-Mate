import { Route, Routes } from "react-router-dom";

import Header from "./components/Header";
import ResultsPage from "./pages/ResultsPage";
import SearchPage from "./pages/SearchPage";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 transition-colors dark:bg-slate-950">
      <Header />
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/results/:jobId" element={<ResultsPage />} />
      </Routes>
    </div>
  );
}