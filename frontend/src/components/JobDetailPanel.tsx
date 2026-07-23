import type { JobPosting } from "../api/jobs";
import { CoverLetterAssistant } from "./CoverLetterAssistant";

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

interface JobDetailPanelProps {
  job: JobPosting | null;
  isSelected: boolean;
  onToggleSelected: () => void;
  profileText: string;
}

export function JobDetailPanel({
  job,
  isSelected,
  onToggleSelected,
  profileText,
}: JobDetailPanelProps) {
  if (!job) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">
        Elegí un puesto de la lista para ver el detalle.
      </div>
    );
  }

  const title = job.title_normalized ?? job.title_raw;
  const company = job.company_normalized ?? job.company_raw;
  const salary = formatSalary(job);
  const isEnriched = job.enrichment_status === "done";

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">{title}</h2>
          <p className="text-slate-600">{company}</p>
          {job.location_raw && <p className="text-sm text-slate-400">{job.location_raw}</p>}
        </div>
        <button
          onClick={onToggleSelected}
          className={`shrink-0 rounded-md px-3 py-1.5 text-sm font-medium ${
            isSelected ? "bg-amber-500 text-white" : "bg-slate-100 text-slate-600"
          }`}
        >
          {isSelected ? "★ Seleccionado" : "☆ Seleccionar"}
        </button>
      </div>

      {isEnriched && (
        <div className="mb-4 flex flex-wrap gap-2 text-xs">
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

      {job.summary && <p className="mb-4 text-sm text-slate-700">{job.summary}</p>}

      {job.requirements && job.requirements.length > 0 && (
        <div className="mb-4">
          <h3 className="mb-1 text-sm font-semibold text-slate-900">Requisitos</h3>
          <div className="flex flex-wrap gap-1.5">
            {job.requirements.map((req) => (
              <span key={req} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
                {req}
              </span>
            ))}
          </div>
        </div>
      )}

      {!isEnriched && (
        <p className="mb-4 text-xs text-slate-400">
          Este aviso todavía no fue analizado con IA — probá "Analizar con IA" para ver
          seniority, modalidad, salario y resumen.
        </p>
      )}

      <CoverLetterAssistant jobId={job.id} profileText={profileText} />

      <div className="mb-4">
        <h3 className="mb-1 text-sm font-semibold text-slate-900">Descripción original</h3>
        <p className="whitespace-pre-line text-sm text-slate-600">{job.description_raw}</p>
      </div>

      <a
        href={job.url}
        target="_blank"
        rel="noreferrer"
        className="inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Ver aviso original →
      </a>
    </div>
  );
}
