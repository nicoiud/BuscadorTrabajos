import type { JobLanguageCode, SearchPreferences } from "../hooks/usePreferences";

const LANGUAGE_LABELS: Record<JobLanguageCode, string> = {
  es: "Español",
  en: "Inglés",
  pt: "Portugués",
  other: "Otros",
};

interface SearchPreferencesPanelProps {
  preferences: SearchPreferences;
  onChange: (preferences: SearchPreferences) => void;
}

export function SearchPreferencesPanel({ preferences, onChange }: SearchPreferencesPanelProps) {
  function toggleLanguage(lang: JobLanguageCode) {
    const languages = preferences.languages.includes(lang)
      ? preferences.languages.filter((l) => l !== lang)
      : [...preferences.languages, lang];
    onChange({ ...preferences, languages });
  }

  return (
    <div className="mb-3 rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="mb-3">
        <p className="mb-1 text-xs font-medium text-slate-500">Idiomas de los avisos a mostrar</p>
        <div className="flex flex-wrap gap-3">
          {(Object.keys(LANGUAGE_LABELS) as JobLanguageCode[]).map((lang) => (
            <label key={lang} className="flex items-center gap-1.5 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={preferences.languages.includes(lang)}
                onChange={() => toggleLanguage(lang)}
              />
              {LANGUAGE_LABELS[lang]}
            </label>
          ))}
        </div>
        {preferences.languages.length === 0 && (
          <p className="mt-1 text-xs text-amber-600">Sin idiomas seleccionados no se filtra nada.</p>
        )}
      </div>

      <div>
        <label className="flex items-center gap-1.5 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={preferences.restrictOnsiteLocation}
            onChange={(e) => onChange({ ...preferences, restrictOnsiteLocation: e.target.checked })}
          />
          Si un aviso es presencial, mostrar solo si la ubicación coincide con:
        </label>
        <input
          type="text"
          value={preferences.onsiteLocation}
          onChange={(e) => onChange({ ...preferences, onsiteLocation: e.target.value })}
          disabled={!preferences.restrictOnsiteLocation}
          placeholder="Ej: Ciudad Autónoma de Buenos Aires, Argentina"
          className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-slate-500 focus:outline-none disabled:bg-slate-100 disabled:text-slate-400"
        />
        <p className="mt-1 text-xs text-slate-500">
          Los avisos remotos o híbridos nunca se filtran por esto.
        </p>
      </div>
    </div>
  );
}
