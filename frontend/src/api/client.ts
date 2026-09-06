import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

export interface Paper {
  external_id: string;
  source: "arxiv" | "semantic_scholar" | "pubmed";
  title: string;
  authors: string[];
  abstract: string | null;
  published_date: string | null;
  pdf_url: string | null;
  doi: string | null;
  url: string | null;
}

export interface SearchResponse {
  topic: string;
  total_results: number;
  results: Paper[];
}

export async function checkHealth(): Promise<{ status: string; env: string }> {
  const { data } = await apiClient.get("/health");
  return data;
}

export async function searchPapers(topic: string, maxResults = 10): Promise<SearchResponse> {
  const { data } = await apiClient.post<SearchResponse>("/api/search", {
    topic,
    max_results: maxResults,
  });
  return data;
}
