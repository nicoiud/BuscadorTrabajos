import { useEffect, useState } from "react";

import { JobDetailPanel } from "../components/JobDetailPanel";
import { JobListRow } from "../components/JobListRow";
import { SearchPreferencesPanel } from "../components/SearchPreferencesPanel";
import { useJobs, useTriggerEnrichment, useTriggerIngestion, type SearchMode } from "../hooks/useJobs";
import { usePreferences } from "../hooks/usePreferences";
import { useProfile } from "../hooks/useProfile";
import { useSelectedJobs } from "../hooks/useSelectedJobs";

export function JobInbox() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("keyword");
  const [openJobId, setOpenJobId] = useState<string | null>(null);
  const [showProfile, setShowProfile] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);

  const { preferences, setPreferences } = usePreferences();
  const { data, isLoading, isError } = useJobs(query, mode, preferences);
  const ingestion = useTriggerIngestion();
  const enrichment = useTriggerEnrichment();
  const { isSelected, toggle, count: selectedCount } = useSelectedJobs();
  const { profileText, setProfileText } = useProfile();

  const items = data?.items ?? [];
  const openJob = items.find((job) => job.id === openJobId) ?? null;

  useEffect(() => {
    if (openJobId && !items.some((job) => job.id === openJobId)) {
      setOpenJobId(null);
    }
  }, [items, openJobId]);

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b border-slate-200 px-6 py-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">BuscadorTrabajos</h1>
            <p className="text-sm text-slate-600">
              {selectedCount > 0 ? `${selectedCount} puesto(s) seleccionado(s)` : "Bandeja de puestos encontrados"}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowProfile((v) => !v)}
              className="rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            >
              Mi perfil
            </button>
            <button
              onClick={() => setShowPreferences((v) => !v)}
              className="rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            >
              Preferencias
            </button>
            <button
              onClick={() => ingestion.mutate()}
              disabled={ingestion.isPending}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {ingestion.isPending ? "Actualizando..." : "Actualizar ofertas"}
            </button>
            <button
              onClick={() => enrichment.mutate()}
              disabled={enrichment.isPending}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {enrichment.isPending ? "Analizando..." : "Analizar con IA"}
            </button>
          </div>
        </div>

        {showProfile && (
          <div className="mb-3 rounded-md border border-slate-200 bg-slate-50 p-3">
            <label className="mb-1 block text-xs font-medium text-slate-500">
              Tu perfil/CV (se guarda en este navegador, se usa para generar cartas de
              presentación con IA)
            </label>
            <textarea
              value={profileText}
              onChange={(e) => setProfileText(e.target.value)}
              rows={4}
              placeholder="Ej: Desarrollador backend con 5 años de experiencia en Python y AWS, buscando roles remotos senior..."
              className="w-full rounded-md border border-slate-300 p-2 text-sm focus:border-slate-500 focus:outline-none"
            />
          </div>
        )}

        {showPreferences && (
          <SearchPreferencesPanel preferences={preferences} onChange={setPreferences} />
        )}

        <div className="flex gap-2">
          <div className="flex gap-1 text-sm">
            <button
              onClick={() => setMode("keyword")}
              className={`rounded-md px-3 py-1.5 font-medium ${
                mode === "keyword" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              Palabra clave
            </button>
            <button
              onClick={() => setMode("semantic")}
              className={`rounded-md px-3 py-1.5 font-medium ${
                mode === "semantic" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              Búsqueda con IA
            </button>
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              mode === "semantic"
                ? "Ej: trabajo remoto de backend Python, senior, buen salario"
                : "Buscar por palabra clave (ej. python, remote, frontend)"
            }
            className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-slate-500 focus:outline-none"
          />
        </div>

        {ingestion.isSuccess && (
          <p className="mt-2 text-xs text-slate-500">
            {ingestion.data.fetched} ofertas procesadas ({ingestion.data.created} nuevas,{" "}
            {ingestion.data.updated} actualizadas).
          </p>
        )}
        {enrichment.isSuccess && (
          <p className="mt-1 text-xs text-slate-500">
            {enrichment.data.enriched} ofertas normalizadas con IA
            {enrichment.data.failed > 0 && `, ${enrichment.data.failed} fallaron`}.
          </p>
        )}
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="w-full max-w-md shrink-0 overflow-y-auto border-r border-slate-200 md:max-w-sm">
          {mode === "semantic" && query.trim().length === 0 && (
            <p className="p-4 text-sm text-slate-500">Escribí qué tipo de trabajo buscás.</p>
          )}
          {isLoading && <p className="p-4 text-sm text-slate-500">Cargando...</p>}
          {isError && <p className="p-4 text-sm text-red-600">No se pudieron cargar las ofertas.</p>}

          {data && items.length === 0 && !isLoading && (
            <p className="p-4 text-sm text-slate-500">
              {mode === "semantic"
                ? "Sin resultados. Probá primero \"Actualizar ofertas\" y \"Analizar con IA\"."
                : "Todavía no hay ofertas. Probá \"Actualizar ofertas\" para traer datos de RemoteOK."}
            </p>
          )}

          {items.map((job) => (
            <JobListRow
              key={job.id}
              job={job}
              isOpen={job.id === openJobId}
              isSelected={isSelected(job.id)}
              onOpen={() => setOpenJobId(job.id)}
              onToggleSelected={() => toggle(job.id)}
            />
          ))}
        </div>

        <div className="hidden min-w-0 flex-1 md:block">
          <JobDetailPanel
            key={openJob?.id ?? "none"}
            job={openJob}
            isSelected={openJob ? isSelected(openJob.id) : false}
            onToggleSelected={() => openJob && toggle(openJob.id)}
            profileText={profileText}
          />
        </div>
      </div>

      {openJob && (
        <div className="fixed inset-0 z-10 bg-white md:hidden">
          <button
            onClick={() => setOpenJobId(null)}
            className="m-2 rounded-md bg-slate-100 px-3 py-1.5 text-sm text-slate-700"
          >
            ← Volver
          </button>
          <JobDetailPanel
            key={openJob.id}
            job={openJob}
            isSelected={isSelected(openJob.id)}
            onToggleSelected={() => toggle(openJob.id)}
            profileText={profileText}
          />
        </div>
      )}
    </div>
  );
}
