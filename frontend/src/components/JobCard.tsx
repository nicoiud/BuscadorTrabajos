import type { JobPosting } from "../api/jobs";

const REGION_LABELS: Record<JobPosting["region"], string> = {
  latam: "Latam",
  remote_intl: "Remoto internacional",
  other: "Otro",
};

export function JobCard({ job }: { job: JobPosting }) {
  return (
    <a
      href={job.url}
      target="_blank"
      rel="noreferrer"
      className="block rounded-lg border border-slate-200 p-4 hover:border-slate-400 hover:shadow-sm transition"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-slate-900">{job.title_raw}</h3>
          <p className="text-sm text-slate-600">{job.company_raw}</p>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">
          {REGION_LABELS[job.region]}
        </span>
      </div>
      {job.location_raw && <p className="mt-2 text-sm text-slate-500">{job.location_raw}</p>}
    </a>
  );
}
