import { useEffect, useState } from "react";

export type JobLanguageCode = "es" | "en" | "pt" | "other";

export interface SearchPreferences {
  languages: JobLanguageCode[];
  restrictOnsiteLocation: boolean;
  onsiteLocation: string;
}

const STORAGE_KEY = "buscadortrabajos:search-preferences";

const DEFAULT_PREFERENCES: SearchPreferences = {
  languages: ["es", "en"],
  restrictOnsiteLocation: true,
  onsiteLocation: "Ciudad Autónoma de Buenos Aires, Argentina",
};

function loadPreferences(): SearchPreferences {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return DEFAULT_PREFERENCES;
  try {
    return { ...DEFAULT_PREFERENCES, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function usePreferences() {
  const [preferences, setPreferences] = useState<SearchPreferences>(() => loadPreferences());

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  }, [preferences]);

  return { preferences, setPreferences };
}
