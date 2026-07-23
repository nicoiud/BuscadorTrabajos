import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "buscadortrabajos:selected-jobs";

function loadSelected(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

export function useSelectedJobs() {
  const [selected, setSelected] = useState<Set<string>>(() => loadSelected());

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...selected]));
  }, [selected]);

  const toggle = useCallback((jobId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
      }
      return next;
    });
  }, []);

  const isSelected = useCallback((jobId: string) => selected.has(jobId), [selected]);

  return { selected, toggle, isSelected, count: selected.size };
}
