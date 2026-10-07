// All calls to the backend live in this one file.
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

const idsParam = (paperIds) => ({ paper_ids: paperIds.join(",") });

export async function checkHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}

// Starts the agent. `field` is the user's own research field (null = auto-detect).
export async function runAgent({ topic, maxPapers = 5, yearFrom, yearTo, field }) {
  const { data } = await apiClient.post("/api/agent/run", {
    topic,
    max_papers: maxPapers,
    year_from: yearFrom || null,
    year_to: yearTo || null,
    field: field || null,
  });
  return data;
}

export async function getAgentStatus(jobId) {
  const { data } = await apiClient.get(`/api/agent/status/${jobId}`);
  return data;
}

export async function getComparison(paperIds) {
  const { data } = await apiClient.get("/api/compare", { params: idsParam(paperIds) });
  return data;
}

export async function getGraphView(paperIds) {
  const { data } = await apiClient.get("/api/graph/view", { params: idsParam(paperIds) });
  return data;
}

export async function getGaps(paperIds) {
  const { data } = await apiClient.get("/api/gaps", { params: idsParam(paperIds) });
  return data;
}

export async function draftRelatedWork(paperIds) {
  const { data } = await apiClient.post("/api/draft-related-work", { paper_ids: paperIds });
  return data;
}

export async function signup(email, password) {
  const { data } = await apiClient.post("/api/auth/signup", { email, password });
  return data;
}

export async function login(email, password) {
  const { data } = await apiClient.post("/api/auth/login", { email, password });
  return data;
}
