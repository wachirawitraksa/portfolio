"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import type { Lang } from "../lib";

// The server reads this cookie to render <html data-theme>; the attribute is also set here so the switch is instant.
export function useTheme(initial: "dark" | "light") {
  const [theme, setTheme] = useState(initial);
  const set = (next: "dark" | "light") => {
    document.documentElement.dataset.theme = next;
    document.cookie = `theme=${next}; path=/; max-age=31536000; samesite=lax`;
    setTheme(next);
  };
  const toggle = () => set(theme === "dark" ? "light" : "dark");
  return { theme, toggle, set };
}

// Language lives in the URL (/th, /en), so switching is a navigation to the same page under the other prefix.
export function useLangSwitch(lang: Lang) {
  const pathname = usePathname();
  const router = useRouter();
  return (to: Lang) => {
    if (to === lang) return;
    router.push(pathname.replace(/^\/(th|en)(?=\/|$)/, `/${to}`));
  };
}
