"use client";

import { useEffect } from "react";
import { useShell, type OutlineItem } from "./shell-context";

// Puts this page's headings in the sidebar outline while the page is open.
export function PageOutline({ items }: { items: OutlineItem[] }) {
  const { setOutline } = useShell();
  const key = items.map((i) => `${i.id}:${i.label}`).join("|");
  useEffect(() => {
    setOutline(items);
    return () => setOutline(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` is the content of `items`
  }, [key, setOutline]);
  return null;
}
