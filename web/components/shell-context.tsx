"use client";

import { createContext, useContext } from "react";
import type { Dict } from "../i18n";
import type { Lang } from "../lib";
import type { SectionId, ShellData } from "../shell-data";

// What the page sections need from the shell (open the CV dialog, show a toast, jump to a section).
export type ShellApi = {
  lang: Lang;
  t: Dict;
  data: ShellData;
  openResume: () => void;
  copyEmail: () => void;
  toast: (message: string) => void;
  goTo: (id: SectionId) => void;
};

export const ShellContext = createContext<ShellApi | null>(null);

export function useShell(): ShellApi {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error("useShell must be used inside <Shell>");
  return ctx;
}
