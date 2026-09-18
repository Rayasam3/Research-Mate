import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export async function checkHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}

export async function runAgent(topic, maxPapers = 5, yearFrom, yearTo) {
  const { data } = await apiClient.post("/api/agent/run", {
    topic,
    max_papers: maxPapers,
    year_from: yearFrom || null,
    year_to: yearTo || null,
  });
  return data;
}

export async function getAgentStatus(jobId) {
  const { data } = await apiClient.get(`/api/agent/status/${jobId}`);
  return data;
}

export async function getComparison(paperIds) {
  const { data } = await apiClient.get("/api/compare", {
    params: { paper_ids: paperIds.join(",") },
  });
  return data;
}

export async function getGaps(paperIds) {
  const { data } = await apiClient.get("/api/gaps", {
    params: { paper_ids: paperIds.join(",") },
  });
  return data;
}

export async function draftRelatedWork(paperIds) {
  const { data } = await apiClient.post("/api/draft-related-work", {
    paper_ids: paperIds,
  });
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