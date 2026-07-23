import type { JobPosting } from "../api/jobs";

const REGION_LABELS: Record<JobPosting["region"], string> = {
  latam: "Latam",
  remote_intl: "Remoto internacional",
  other: "Otro",
};

interface JobListRowProps {
  job: JobPosting;
  isOpen: boolean;
  isSelected: boolean;
  onOpen: () => void;
  onToggleSelected: () => void;
}

export function JobListRow({ job, isOpen, isSelected, onOpen, onToggleSelected }: JobListRowProps) {
  const title = job.title_normalized ?? job.title_raw;
  const company = job.company_normalized ?? job.company_raw;
  const snippet = job.summary ?? job.description_raw.replace(/<[^>]+>/g, "").slice(0, 140);

  return (
    <div
      onClick={onOpen}
      className={`flex cursor-pointer items-start gap-3 border-b border-slate-100 px-3 py-3 hover:bg-slate-50 ${
        isOpen ? "bg-indigo-50" : isSelected ? "bg-amber-50" : "bg-white"
      }`}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onClick={(e) => e.stopPropagation()}
        onChange={onToggleSelected}
        className="mt-1 shrink-0"
        aria-label={`Seleccionar ${title}`}
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="truncate font-medium text-slate-900">{title}</p>
          <span className="shrink-0 text-xs text-slate-400">{REGION_LABELS[job.region]}</span>
        </div>
        <p className="truncate text-sm text-slate-600">{company}</p>
        <p className="truncate text-xs text-slate-400">{snippet}</p>
      </div>
    </div>
  );
}
