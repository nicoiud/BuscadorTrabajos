import type { JobPosting } from "../api/jobs";

const REGION_LABELS: Record<JobPosting["region"], string> = {
  latam: "Latam",
  remote_intl: "Remoto internacional",
  other: "Otro",
};

const MODALITY_LABELS: Record<NonNullable<JobPosting["modality"]>, string> = {
  remote: "Remoto",
  hybrid: "Híbrido",
  onsite: "Presencial",
};

const SENIORITY_LABELS: Record<NonNullable<JobPosting["seniority"]>, string> = {
  junior: "Junior",
  mid: "Semi-senior",
  senior: "Senior",
  lead: "Lead",
  exec: "Ejecutivo",
};

function formatSalary(job: JobPosting): string | null {
  if (!job.salary_min && !job.salary_max) return null;
  const currency = job.currency ?? "";
  if (job.salary_min && job.salary_max) {
    return `${currency} ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}`;
  }
  return `${currency} ${(job.salary_min ?? job.salary_max)!.toLocaleString()}`;
}

export function JobCard({ job }: { job: JobPosting }) {
  const title = job.title_normalized ?? job.title_raw;
  const company = job.company_normalized ?? job.company_raw;
  const salary = formatSalary(job);
  const isEnriched = job.enrichment_status === "done";

  return (
    <a
      href={job.url}
      target="_blank"
      rel="noreferrer"
      className="block rounded-lg border border-slate-200 p-4 hover:border-slate-400 hover:shadow-sm transition"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-600">{company}</p>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">
          {REGION_LABELS[job.region]}
        </span>
      </div>

      {job.location_raw && <p className="mt-2 text-sm text-slate-500">{job.location_raw}</p>}

      {isEnriched && (
        <div className="mt-2 flex flex-wrap gap-2 text-xs">
          {job.seniority && (
            <span className="rounded-full bg-indigo-50 px-2 py-1 text-indigo-700">
              {SENIORITY_LABELS[job.seniority]}
            </span>
          )}
          {job.modality && (
            <span className="rounded-full bg-emerald-50 px-2 py-1 text-emerald-700">
              {MODALITY_LABELS[job.modality]}
            </span>
          )}
          {salary && (
            <span className="rounded-full bg-amber-50 px-2 py-1 text-amber-700">{salary}</span>
          )}
        </div>
      )}

      {job.summary && <p className="mt-2 text-sm text-slate-600">{job.summary}</p>}

      {job.requirements && job.requirements.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {job.requirements.map((req) => (
            <span key={req} className="rounded bg-slate-50 px-1.5 py-0.5 text-xs text-slate-500">
              {req}
            </span>
          ))}
        </div>
      )}
    </a>
  );
}
