"use client";

import { useCallback, useEffect, useRef } from "react";

const DURATION = 3100; // the bar fills in 2.8s, the fade-out starts at 2.6s (see globals.css)

// The overlay is always in the markup; CSS shows it only while <html data-boot> is set (see the layout's inline
// script). This component ends it: after the animation, on the skip button, or on Esc.
export function Splash({ name, fallback, skip, replay }: { name: string; fallback: string; skip: string; replay: number }) {
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const label = name.trim().split(/\s+/)[0] || fallback;

  const finish = useCallback(() => {
    clearTimeout(timer.current);
    delete document.documentElement.dataset.boot;
    try {
      sessionStorage.setItem("boot", "1");
    } catch {}
  }, []);

  const start = useCallback(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(finish, DURATION);
  }, [finish]);

  // First load: the attribute may already be set by the inline script.
  useEffect(() => {
    if (document.documentElement.dataset.boot) start();
    return () => clearTimeout(timer.current);
  }, [start]);

  // "Replay intro" in the Help menu: remove then set the attribute so the CSS animations restart.
  useEffect(() => {
    if (!replay) return;
    delete document.documentElement.dataset.boot;
    const id = requestAnimationFrame(() => {
      document.documentElement.dataset.boot = "1";
      start();
    });
    return () => cancelAnimationFrame(id);
  }, [replay, start]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && document.documentElement.dataset.boot) finish();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [finish]);

  return (
    <div className="splash splash-fade absolute inset-0 z-10 items-center justify-center overflow-hidden bg-[#1e1e1e] text-[#cccccc]">
      <div aria-hidden="true" className="splash-ring size-[420px] border-t-[#3794ff]" style={{ animationDuration: "24s" }} />
      <div aria-hidden="true" className="splash-ring size-[620px] border-r-[#4ec9b0]" style={{ animationDuration: "36s", animationDirection: "reverse" }} />
      <div className="relative flex max-w-full flex-col items-center gap-[22px] px-5">
        <div className="font-mono text-[13px] text-[#7fb069]">// booting portfolio</div>
        <div className="max-w-full text-[clamp(48px,12vw,96px)] leading-none font-extrabold tracking-tight text-white [overflow-wrap:anywhere]">{label}</div>
        <div className="h-1 w-[min(320px,80vw)] overflow-hidden rounded-sm bg-[#3a3d41]">
          <div className="splash-bar h-full bg-[#3794ff]" />
        </div>
        <button type="button" onClick={finish} className="min-h-9 cursor-pointer rounded-md border border-[#454545] bg-transparent px-3.5 py-1.5 font-mono text-xs text-[#d4d4d4] hover:bg-white/10">
          {skip}
        </button>
      </div>
    </div>
  );
}
