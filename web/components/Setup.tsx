"use client";

import type { Lang } from "../lib";
import { useLangSwitch, useTheme } from "./Toggles";

// Temporary: two buttons to check theme and language switching. Replaced by the title bar in step 2.
export function Setup({ lang, initialTheme, labels }: { lang: Lang; initialTheme: "dark" | "light"; labels: { theme: string; lang: string } }) {
  const { theme, toggle } = useTheme(initialTheme);
  const go = useLangSwitch(lang);
  return (
    <div className="flex gap-3 font-mono text-xs">
      <button type="button" onClick={toggle} className="rounded-md border border-line px-3 py-2 hover:bg-hover">
        {labels.theme}: {theme}
      </button>
      <div role="group" aria-label={labels.lang} className="flex overflow-hidden rounded-md border border-line">
        {(["th", "en"] as const).map((l) => (
          <button key={l} type="button" aria-pressed={l === lang} onClick={() => go(l)} className={`px-3 py-2 ${l === lang ? "bg-brand text-white" : "hover:bg-hover"}`}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}
