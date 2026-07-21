import { useState } from "react";

import { JobCard } from "../components/JobCard";
import { useJobs, useTriggerEnrichment, useTriggerIngestion, type SearchMode } from "../hooks/useJobs";

export function JobSearch() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("keyword");
  const { data, isLoading, isError } = useJobs(query, mode);
  const ingestion = useTriggerIngestion();
  const enrichment = useTriggerEnrichment();

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">BuscadorTrabajos</h1>
        <p className="text-slate-600">Ofertas de empleo agregadas y normalizadas con IA.</p>
      </header>

      <div className="mb-4 flex gap-2 text-sm">
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

      <div className="mb-6 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={
            mode === "semantic"
              ? "Ej: trabajo remoto de backend Python, senior, buen salario"
              : "Buscar por palabra clave (ej. python, remote, frontend)"
          }
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 focus:border-slate-500 focus:outline-none"
        />
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

      {ingestion.isSuccess && (
        <p className="mb-2 text-sm text-slate-500">
          {ingestion.data.fetched} ofertas procesadas ({ingestion.data.created} nuevas,{" "}
          {ingestion.data.updated} actualizadas).
        </p>
      )}
      {enrichment.isSuccess && (
        <p className="mb-4 text-sm text-slate-500">
          {enrichment.data.enriched} ofertas normalizadas con IA
          {enrichment.data.failed > 0 && `, ${enrichment.data.failed} fallaron`}.
        </p>
      )}

      {mode === "semantic" && query.trim().length === 0 && (
        <p className="text-slate-500">Escribí qué tipo de trabajo buscás.</p>
      )}
      {isLoading && <p className="text-slate-500">Cargando...</p>}
      {isError && <p className="text-red-600">No se pudieron cargar las ofertas.</p>}

      {data && (
        <>
          <p className="mb-3 text-sm text-slate-500">{data.total} resultado(s)</p>
          <div className="space-y-3">
            {data.items.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
          {data.items.length === 0 && (
            <p className="text-slate-500">
              {mode === "semantic"
                ? "Sin resultados. Probá primero 'Actualizar ofertas' y 'Analizar con IA'."
                : "Todavía no hay ofertas. Probá \"Actualizar ofertas\" para traer datos de RemoteOK."}
            </p>
          )}
        </>
      )}
    </div>
  );
}
