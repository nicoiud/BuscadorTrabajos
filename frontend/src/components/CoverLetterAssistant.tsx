import { useState } from "react";

import { useGenerateCoverLetter } from "../hooks/useJobs";

interface CoverLetterAssistantProps {
  jobId: string;
  profileText: string;
}

export function CoverLetterAssistant({ jobId, profileText }: CoverLetterAssistantProps) {
  const { mutate, data, isPending, isError } = useGenerateCoverLetter();
  const [copied, setCopied] = useState(false);

  const hasProfile = profileText.trim().length > 0;

  const handleCopy = async () => {
    if (!data) return;
    await navigator.clipboard.writeText(data.cover_letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mb-4 rounded-md border border-slate-200 p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">Asistente de postulación</h3>
        <button
          onClick={() => mutate({ jobId, profileText })}
          disabled={!hasProfile || isPending}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {isPending ? "Generando..." : "Generar carta con IA"}
        </button>
      </div>

      {!hasProfile && (
        <p className="mt-2 text-xs text-slate-400">
          Completá "Mi perfil" arriba (tu CV/resumen) para poder generar la carta.
        </p>
      )}
      {isError && <p className="mt-2 text-xs text-red-600">No se pudo generar la carta.</p>}

      {data && (
        <div className="mt-3 space-y-3">
          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">Borrador de carta</span>
              <button onClick={handleCopy} className="text-xs text-indigo-600 hover:underline">
                {copied ? "¡Copiado!" : "Copiar"}
              </button>
            </div>
            <textarea
              readOnly
              value={data.cover_letter}
              rows={8}
              className="w-full rounded-md border border-slate-200 bg-slate-50 p-2 text-sm text-slate-700"
            />
          </div>
          {data.key_points.length > 0 && (
            <div>
              <span className="text-xs font-medium text-slate-500">Puntos clave reusables</span>
              <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
                {data.key_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
