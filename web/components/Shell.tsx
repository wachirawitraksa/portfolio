"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Dict } from "../i18n";
import type { Lang } from "../lib";
import type { SectionId, ShellData } from "../shell-data";
import { fileInfo } from "./files";
import { FileIcon, GithubIcon, MailIcon } from "./icons";
import { ResumeDialog } from "./ResumeDialog";
import { Sidebar } from "./Sidebar";
import { ShellContext, type ShellApi } from "./shell-context";
import { TitleBar, type Menu } from "./TitleBar";
import { useLangSwitch, useTheme } from "./Toggles";

type Props = { lang: Lang; t: Dict; data: ShellData; initialTheme: "dark" | "light"; children: ReactNode };

// Wide screens show the sidebar inline; narrower ones turn it into a drawer. Both states are CSS-driven
// so the server and the browser render the same first paint at any width.
const WIDE = "(min-width: 901px)";

export function Shell({ lang, t, data, initialTheme, children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const onHome = pathname === `/${lang}`;
  const { theme, toggle: toggleTheme } = useTheme(initialTheme);
  const switchLang = useLangSwitch(lang);

  const [sidebarWide, setSidebarWide] = useState(true);
  const [drawer, setDrawer] = useState(false);
  const [menu, setMenu] = useState<string | null>(null);
  const [resume, setResume] = useState(false);
  const [message, setMessage] = useState("");
  const [active, setActive] = useState<SectionId>("home");
  const scroller = useRef<HTMLDivElement>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const hasCv = Boolean(data.cvTh || data.cvEn);

  const toast = useCallback((text: string) => {
    setMessage(text);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setMessage(""), 2200);
  }, []);

  const toggleSidebar = useCallback(() => {
    if (window.matchMedia(WIDE).matches) setSidebarWide((v) => !v);
    else setDrawer((v) => !v);
  }, []);

  const goTo = useCallback(
    (id: SectionId) => {
      setMenu(null);
      setDrawer(false);
      if (onHome) document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
      else router.push(`/${lang}#${id}`);
    },
    [onHome, router, lang],
  );

  const copyEmail = useCallback(() => {
    setMenu(null);
    navigator.clipboard?.writeText(data.email).then(() => toast(t.emailCopied), () => {});
  }, [data.email, t.emailCopied, toast]);

  const openResume = useCallback(() => {
    setMenu(null);
    setDrawer(false);
    setResume(true);
  }, []);

  // Keyboard: Ctrl+B toggles the sidebar, Esc closes whatever is open on top.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        toggleSidebar();
      } else if (e.key === "Escape") {
        setMenu(null);
        setResume(false);
        setDrawer(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleSidebar]);

  // Highlight the explorer entry for the section being read.
  useEffect(() => {
    const root = scroller.current;
    if (!root || !onHome) return;
    const targets = data.sections.map((id) => document.getElementById(id)).filter((el): el is HTMLElement => Boolean(el));
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id as SectionId);
      },
      { root, rootMargin: "-20% 0px -70% 0px" },
    );
    targets.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [onHome, data.sections, pathname]);

  const menus: Menu[] = useMemo(() => {
    const close = (fn: () => void) => () => {
      setMenu(null);
      fn();
    };
    const file: Menu["items"] = [];
    if (hasCv) file.push({ label: t.openResume, run: openResume });
    if (data.cvTh) file.push({ label: t.downloadCvTh, run: close(() => window.open(data.cvTh!, "_blank")) });
    if (data.cvEn) file.push({ label: t.downloadCvEn, run: close(() => window.open(data.cvEn!, "_blank")) });
    if (data.email) file.push({ label: t.copyEmail, run: copyEmail });

    const view: Menu["items"] = [
      { label: t.sidebarShort, key: "Ctrl+B", run: close(toggleSidebar) },
      { label: t.themeBtn, run: close(toggleTheme) },
      { label: t.switchLang, run: close(() => switchLang(lang === "th" ? "en" : "th")) },
    ];
    const go: Menu["items"] = data.sections.map((id) => ({ label: fileInfo(id, data).name, run: () => goTo(id) }));
    const help: Menu["items"] = [{ label: t.shortcuts, run: close(() => toast("Ctrl+B · Esc")) }];
    if (data.github) help.push({ label: t.viewGithub, key: "↗", run: close(() => window.open(data.github!, "_blank", "noopener")) });

    return [
      ...(file.length ? [{ id: "file", label: "File", items: file }] : []),
      { id: "view", label: "View", items: view },
      { id: "go", label: "Go", items: go },
      { id: "help", label: "Help", items: help },
    ];
  }, [t, data, hasCv, lang, openResume, copyEmail, toggleSidebar, toggleTheme, switchLang, goTo, toast]);

  const api: ShellApi = { lang, t, data, openResume, copyEmail, toast, goTo };
  const activeName = onHome ? fileInfo(active, data).name : (data.kinds[0]?.file ?? "home.tsx");
  const act = "flex size-11 cursor-pointer items-center justify-center rounded-md text-[#bdbdbd] hover:bg-hover";
  const bar = "h-[22px] cursor-pointer rounded-[3px] border-0 bg-transparent px-2 text-white hover:bg-white/15";

  return (
    <ShellContext.Provider value={api}>
      <div className="relative flex h-dvh w-full flex-col overflow-hidden bg-bg text-fg">
        {menu && <button type="button" onClick={() => setMenu(null)} aria-label={t.close} className="absolute inset-0 z-[6] cursor-default border-0 bg-transparent" />}

        <TitleBar
          t={t}
          lang={lang}
          theme={theme}
          title={`${activeName} — ${data.slug}`}
          menus={menus}
          openMenu={menu}
          setOpenMenu={setMenu}
          drawerOpen={drawer}
          onSidebar={toggleSidebar}
          onLang={switchLang}
          onTheme={toggleTheme}
        />

        <div className="relative flex min-h-0 flex-1">
          <nav aria-label="Toolbar" className="hidden w-12 shrink-0 flex-col items-center gap-0.5 bg-act pt-1.5 sm:flex">
            <button type="button" onClick={toggleSidebar} aria-label={t.sidebarBtn} title={t.sidebarBtn} className={`${act} text-[#e5e5e5]`}>
              <FileIcon />
            </button>
            {data.github && (
              <a href={data.github} target="_blank" rel="noopener" aria-label="GitHub" title="GitHub" className={act}>
                <GithubIcon />
              </a>
            )}
            <button type="button" onClick={() => goTo("contact")} aria-label={t.contact} title={t.contact} className={act}>
              <MailIcon />
            </button>
          </nav>

          {drawer && <button type="button" onClick={() => setDrawer(false)} aria-label={t.close} className="absolute inset-0 z-[7] cursor-default border-0 bg-scrim ide:hidden" />}
          <Sidebar
            data={data}
            t={t}
            active={active}
            hasCv={hasCv}
            goTo={goTo}
            openResume={openResume}
            className={`${drawer ? "absolute top-0 bottom-0 left-0 z-[8] flex w-[min(280px,85vw)] shadow-2xl sm:left-12 sm:w-[220px]" : "hidden"} ${sidebarWide ? "ide:static ide:flex ide:shadow-none" : "ide:hidden"}`}
          />

          <main className="flex min-w-0 flex-1 flex-col">
            <div role="tablist" className="flex h-9 shrink-0 overflow-x-auto border-b border-line bg-side">
              <div role="tab" aria-selected="true" className="flex items-center border-t-2 border-brand bg-bg px-4 font-mono text-[13px] whitespace-nowrap text-strong">
                {activeName}
              </div>
            </div>
            <div ref={scroller} className="relative min-h-0 flex-1 scroll-smooth overflow-x-hidden overflow-y-auto">
              {children}
            </div>
          </main>

          {resume && hasCv && <ResumeDialog data={data} t={t} onClose={() => setResume(false)} />}
          {message && (
            <div role="status" className="absolute bottom-3 left-1/2 z-[9] -translate-x-1/2 rounded-lg border border-white/15 bg-black px-4 py-2.5 font-mono text-xs whitespace-nowrap text-white">
              <span className="text-[#4ade80]">✓</span> {message}
            </div>
          )}
        </div>

        <footer className="flex h-[26px] shrink-0 items-center gap-1 overflow-hidden bg-[#007acc] px-1.5 font-mono text-xs whitespace-nowrap text-white">
          <button type="button" onClick={toggleSidebar} className={`${bar} hidden sm:block`}>
            Ctrl+B {t.sidebarShort}
          </button>
          <button type="button" onClick={() => switchLang(lang === "th" ? "en" : "th")} className={`${bar} ml-auto`}>
            {t.langLabel}
          </button>
          <button type="button" onClick={toggleTheme} className={bar}>
            {theme === "dark" ? t.themeDark : t.themeLight}
          </button>
        </footer>
      </div>
    </ShellContext.Provider>
  );
}
