import { useEffect, useState } from "react";

const STORAGE_KEY = "buscadortrabajos:profile-text";

function loadProfile(): string {
  return localStorage.getItem(STORAGE_KEY) ?? "";
}

export function useProfile() {
  const [profileText, setProfileText] = useState<string>(() => loadProfile());

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, profileText);
  }, [profileText]);

  return { profileText, setProfileText };
}
