import { useCallback, useEffect, useState } from "react";

export function useTheme() {
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains("dark")
  );

  const toggle = useCallback(() => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.theme = next ? "dark" : "light";
    setDark(next);
  }, [dark]);

  return { dark, toggle };
}
