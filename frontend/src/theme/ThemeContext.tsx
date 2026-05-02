import React, { createContext, useContext, useState, useCallback, useMemo } from "react";
import type { FraxThemeColors, ThemeMode } from "./themeTokens";
import { lightTheme, darkTheme } from "./themeTokens";

interface ThemeContextValue {
  mode: ThemeMode;
  colors: FraxThemeColors;
  toggle: () => void;
  setMode: (m: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<ThemeMode>("light");

  const colors = useMemo(() => (mode === "light" ? lightTheme : darkTheme), [mode]);

  const toggle = useCallback(() => {
    setModeState((prev) => (prev === "light" ? "dark" : "light"));
  }, []);

  const setMode = useCallback((m: ThemeMode) => setModeState(m), []);

  const value = useMemo(() => ({ mode, colors, toggle, setMode }), [mode, colors, toggle, setMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}
