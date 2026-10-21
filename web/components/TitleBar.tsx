"use client";

import type { Dict } from "../i18n";
import type { Lang } from "../lib";
import { MenuIcon, MoonIcon, SunIcon } from "./icons";

export type MenuItem = { label: string; key?: string; run: () => void };
export type Menu = { id: string; label: string; items: MenuItem[] };

type Props = {
  t: Dict;
  lang: Lang;
  theme: "dark" | "light";
  title: string;
  menus: Menu[];
  openMenu: string | null;
  setOpenMenu: (id: string | null) => void;
  drawerOpen: boolean;
  onSidebar: () => void;
  onLang: (to: Lang) => void;
  onTheme: () => void;
};

export function TitleBar({ t, lang, theme, title, menus, openMenu, setOpenMenu, drawerOpen, onSidebar, onLang, onTheme }: Props) {
  const ghost = "cursor-pointer rounded-md hover:bg-hover";
  return (
    <header className="relative z-[7] flex h-10 shrink-0 items-center gap-3 border-b border-line bg-title px-3 text-[13px]">
      <div className="hidden gap-2 sm:flex" aria-hidden="true">
        <span className="size-3 rounded-full bg-[#ff5f57]" />
        <span className="size-3 rounded-full bg-[#febc2e]" />
        <span className="size-3 rounded-full bg-[#28c840]" />
      </div>
      <nav aria-label={t.menubar} className="relative z-[7] hidden gap-0.5 ide:flex">
        {menus.map((m) => {
          const open = openMenu === m.id;
          return (
            <div key={m.id} className="relative">
              <button
                type="button"
                onClick={() => setOpenMenu(open ? null : m.id)}
                aria-expanded={open}
                aria-haspopup="menu"
                className={`h-7 px-2.5 ${open ? "cursor-pointer rounded-[5px] bg-sel text-strong" : ghost}`}
              >
                {m.label}
              </button>
              {open && (
                <div role="menu" className="absolute top-8 left-0 flex min-w-60 flex-col rounded-lg border border-line bg-side p-1.5 shadow-xl">
                  {m.items.map((it) => (
                    <button key={it.label} type="button" role="menuitem" onClick={it.run} className={`flex justify-between gap-6 px-2.5 py-2 text-left text-[13px] text-fg ${ghost}`}>
                      <span>{it.label}</span>
                      <span className="font-mono text-xs text-muted">{it.key}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>
      <button
        type="button"
        onClick={onSidebar}
        aria-label={t.sidebarBtn}
        aria-expanded={drawerOpen}
        className={`flex h-8 w-9 items-center justify-center border border-line sm:hidden ${ghost}`}
      >
        <MenuIcon />
      </button>
      <div className="min-w-0 flex-1 truncate text-center font-mono text-xs text-muted">{title}</div>
      <div role="group" aria-label={t.langGroup} className="flex overflow-hidden rounded-md border border-line font-mono text-xs">
        {(["th", "en"] as const).map((l) => (
          <button
            key={l}
            type="button"
            aria-pressed={l === lang}
            onClick={() => onLang(l)}
            className={`h-7 cursor-pointer px-2.5 ${l === lang ? "bg-brand text-white" : "hover:bg-hover"}`}
          >
            {l.toUpperCase()}
          </button>
        ))}
      </div>
      <button type="button" onClick={onTheme} aria-label={t.themeBtn} title={t.themeBtn} className={`flex h-[30px] w-8 items-center justify-center border border-line ${ghost}`}>
        {theme === "dark" ? <SunIcon /> : <MoonIcon />}
      </button>
    </header>
  );
}
