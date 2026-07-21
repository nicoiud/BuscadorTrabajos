export interface JobPosting {
  id: string;
  title_raw: string;
  company_raw: string;
  description_raw: string;
  url: string;
  location_raw: string | null;
  posted_at: string | null;
  language: "es" | "en";
  region: "latam" | "remote_intl" | "other";
}

export interface JobPostingList {
  total: number;
  items: JobPosting[];
}

export interface IngestResult {
  source_slug: string;
  fetched: number;
  created: number;
  updated: number;
}

const API_BASE = "/api/v1";

export async function fetchJobs(query: string): Promise<JobPostingList> {
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());

  const response = await fetch(`${API_BASE}/jobs?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Error al buscar empleos: ${response.status}`);
  }
  return response.json();
}

export async function triggerRemoteOkIngestion(): Promise<IngestResult> {
  const response = await fetch(`${API_BASE}/jobs/ingest/remoteok`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Error al disparar la ingestion: ${response.status}`);
  }
  return response.json();
}
