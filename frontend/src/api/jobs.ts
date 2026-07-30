import type { SearchPreferences } from "../hooks/usePreferences";

export interface JobPosting {
  id: string;
  title_raw: string;
  company_raw: string;
  description_raw: string;
  url: string;
  location_raw: string | null;
  posted_at: string | null;
  language: "es" | "en" | "pt" | "other";
  region: "latam" | "remote_intl" | "other";

  title_normalized: string | null;
  company_normalized: string | null;
  seniority: "junior" | "mid" | "senior" | "lead" | "exec" | null;
  modality: "remote" | "hybrid" | "onsite" | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  requirements: string[] | null;
  summary: string | null;
  enrichment_status: "pending" | "done" | "failed";
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
  error: string | null;
}

export interface IngestSummary {
  results: IngestResult[];
  total_fetched: number;
  total_created: number;
  total_updated: number;
}

export interface EnrichResult {
  processed: number;
  enriched: number;
  failed: number;
}

export interface CoverLetterDraft {
  cover_letter: string;
  key_points: string[];
}

const API_BASE = "/api/v1";

export async function fetchJobs(
  query: string,
  preferences: SearchPreferences,
  offset = 0,
  limit = 20,
): Promise<JobPostingList> {
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  for (const lang of preferences.languages) params.append("languages", lang);
  const onsiteLocation = preferences.onsiteLocation.trim();
  if (preferences.restrictOnsiteLocation && onsiteLocation) {
    params.set("onsite_location", onsiteLocation);
  }
  params.set("offset", String(offset));
  params.set("limit", String(limit));

  const response = await fetch(`${API_BASE}/jobs?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Error al buscar empleos: ${response.status}`);
  }
  return response.json();
}

export async function semanticSearchJobs(
  query: string,
  preferences: SearchPreferences,
  limit = 20,
): Promise<JobPostingList> {
  const onsiteLocation = preferences.onsiteLocation.trim();
  const response = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      limit,
      languages: preferences.languages,
      onsite_location: preferences.restrictOnsiteLocation && onsiteLocation ? onsiteLocation : null,
    }),
  });
  if (!response.ok) {
    throw new Error(`Error en la búsqueda semántica: ${response.status}`);
  }
  return response.json();
}

export async function triggerIngestion(): Promise<IngestSummary> {
  const response = await fetch(`${API_BASE}/jobs/ingest`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Error al disparar la ingestion: ${response.status}`);
  }
  return response.json();
}

export async function triggerEnrichment(): Promise<EnrichResult> {
  const response = await fetch(`${API_BASE}/jobs/enrich`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Error al disparar el enrichment: ${response.status}`);
  }
  return response.json();
}

export async function generateCoverLetter(
  jobId: string,
  profileText: string,
): Promise<CoverLetterDraft> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/cover-letter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_text: profileText }),
  });
  if (!response.ok) {
    throw new Error(`Error al generar la carta: ${response.status}`);
  }
  return response.json();
}
