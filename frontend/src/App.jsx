import { Route, Routes } from "react-router-dom";

import Header from "./components/Header";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import ResultsPage from "./pages/ResultsPage";
import SearchPage from "./pages/SearchPage";

export default function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-slate-50 transition-colors dark:bg-slate-950">
        <Header />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <SearchPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/results/:jobId"
            element={
              <ProtectedRoute>
                <ResultsPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </div>
    </AuthProvider>
  );
}