"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Lang } from "../lib";
import { fileInfo, RESUME_FILE } from "./files";
import { useShell } from "./shell-context";
import type { SectionId } from "../shell-data";

type Line = { t: string; color?: string; prompt?: boolean };

const GREEN = "#22c55e";
const RED = "#f14c4c";
const MUTED = "var(--muted)";
const BRAND = "var(--brand)";

type Props = {
  open: boolean;
  bootKey: number; // bump to (re)run the boot sequence
  onClose: () => void;
  setTheme: (theme: "dark" | "light") => void;
  switchLang: (lang: Lang) => void;
  askAi: (question?: string) => void;
};

// The bottom panel. `npm run boot` is not a recording: it calls the real API and prints what came back and how long it took.
export function Terminal({ open, bootKey, onClose, setTheme, switchLang, askAi }: Props) {
  const { lang, t, data, goTo, openResume } = useShell();
  const [lines, setLines] = useState<Line[]>([]);
  const [typing, setTyping] = useState<string | null>(null); // the boot command while it is being typed
  const [ready, setReady] = useState(false);
  const [input, setInput] = useState("");
  const run = useRef(0); // bumped to cancel a boot that is still going
  const scroller = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const prompt = `${data.slug.replace(/-portfolio$/, "") || "guest"}@portfolio`;

  const push = useCallback((...next: Line[]) => setLines((prev) => [...prev, ...next]), []);

  const boot = useCallback(async () => {
    const id = ++run.current;
    const alive = () => id === run.current;
    const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
    setLines([]);
    setReady(false);
    const cmd = "npm run boot";
    for (let i = 1; i <= cmd.length; i++) {
      setTyping(cmd.slice(0, i));
      await wait(45 + Math.random() * 45);
      if (!alive()) return;
    }
    await wait(200);
    if (!alive()) return;
    setTyping(null);
    push({ t: cmd, prompt: true }, { t: "" }, { t: `> ${data.slug} boot` }, { t: "" });

    const probes: { path: string; label: string }[] = [
      { path: "/api/health", label: "GET /api/health" },
      { path: "/api/profile", label: "GET /api/profile" },
      { path: "/api/projects?limit=1", label: "GET /api/projects" },
    ];
    let failed = false;
    for (const probe of probes) {
      const start = performance.now();
      let status = 0;
      let body: unknown = null;
      try {
        const res = await fetch(probe.path);
        status = res.status;
        body = await res.json().catch(() => null);
      } catch {}
      if (!alive()) return;
      const ms = Math.round(performance.now() - start);
      const ok = status >= 200 && status < 300;
      failed ||= !ok;
      push({ t: ` ${probe.label} ${status || "failed"} in ${ms}ms`, color: ok ? MUTED : RED });
      if (probe.path === "/api/health" && body && typeof body === "object") {
        const h = body as Record<string, unknown>;
        for (const key of ["database", "storage"]) if (key in h) push({ t: `   ${h[key] === "ok" ? "✓" : "✗"} ${key}: ${String(h[key])}`, color: h[key] === "ok" ? GREEN : RED });
      }
      await wait(120);
    }
    push({ t: "" }, failed ? { t: "✗ some checks failed", color: RED } : { t: "✓ ready", color: GREEN }, { t: t.ready, color: BRAND });
    setReady(true);
  }, [data.slug, push, t.ready]);

  useEffect(() => {
    if (bootKey > 0) void boot();
    return () => {
      run.current++;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-run only when asked, not when `boot` is re-created
  }, [bootKey]);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines, typing, ready, open]);

  useEffect(() => {
    if (open && ready) inputRef.current?.focus();
  }, [open, ready]);

  // What `cd`/`open` understand: every file in the explorer, with or without its extension.
  const targets = (): Map<string, SectionId> => {
    const map = new Map<string, SectionId>();
    for (const id of data.sections) {
      const name = fileInfo(id, data).name.toLowerCase();
      map.set(name, id);
      map.set(name.replace(/\/$/, ""), id);
      map.set(name.replace(/\.[a-z]+$/, ""), id);
    }
    map.set("experience", "experience");
    return map;
  };

  const exec = (raw: string) => {
    const q = raw.trim();
    const echo: Line = { t: raw, prompt: true };
    const say = (...out: (string | Line)[]) => {
      push(echo, ...out.map((l) => (typeof l === "string" ? { t: l } : l)));
      setInput("");
    };
    if (!q) return say();
    const [cmd, ...rest] = q.split(/\s+/);
    const arg = rest.join(" ");
    switch (cmd.toLowerCase()) {
      case "clear":
      case "cls":
        setLines([]);
        return setInput("");
      case "exit":
        setInput("");
        return onClose();
      case "help":
        return say(...t.termHelp.split("\n").map((l, i): Line => ({ t: l, color: i === 0 ? BRAND : undefined })));
      case "ls":
        return say({ t: [...data.sections.map((id) => fileInfo(id, data).name), ...(data.cvTh || data.cvEn ? [RESUME_FILE.name] : [])].join("  "), color: BRAND });
      case "pwd":
        return say(`/home/${prompt.split("@")[0]}/${data.slug}`);
      case "whoami":
        return say(data.name || prompt.split("@")[0]);
      case "date":
        return say(new Date().toString().slice(0, 24));
      case "echo":
        return say(arg);
      case "theme": {
        const v = arg.toLowerCase();
        if (v !== "dark" && v !== "light") return say({ t: "usage: theme dark|light", color: RED });
        setTheme(v);
        return say({ t: `✓ theme → ${v}`, color: GREEN });
      }
      case "lang": {
        const v = arg.toLowerCase();
        if (v !== "th" && v !== "en") return say({ t: "usage: lang th|en", color: RED });
        say({ t: `✓ lang → ${v}`, color: GREEN });
        return switchLang(v);
      }
      case "ask":
      case "openchat":
      case "openchat()":
        say({ t: "→ openChat()", color: MUTED });
        return askAi(arg || undefined);
      case "npm":
        if (arg === "run boot") {
          setInput("");
          return void boot();
        }
        return say({ t: `npm: unknown command: ${arg}`, color: RED });
      case "cd":
      case "open":
      case "cat":
      case "code": {
        const key = arg.toLowerCase().replace(/^\.\//, "").replace(/^~\//, "");
        if (["resume.pdf", "resume", "cv"].includes(key) && (data.cvTh || data.cvEn)) {
          say({ t: "opening resume.pdf ...", color: MUTED });
          return openResume();
        }
        if (!key || key === "~" || key === "..") {
          say();
          return goTo("home");
        }
        const id = targets().get(key);
        if (id) {
          say({ t: `→ ${key}`, color: MUTED });
          return goTo(id);
        }
        return say({ t: `${cmd}: no such file or directory: ${arg}`, color: RED });
      }
      default:
        return say({ t: `command not found: ${cmd}`, color: RED });
    }
  };

  const Prompt = () => (
    <>
      <span style={{ color: GREEN }}>{prompt}</span> <span className="text-brand">~</span> %{" "}
    </>
  );

  return (
    <section aria-label="Terminal" className={`${open ? "hidden sm:flex" : "hidden"} h-40 shrink-0 flex-col border-t border-line bg-term font-mono text-xs`} onClick={() => inputRef.current?.focus()}>
      <div className="flex items-center py-1 pr-2 pl-4 text-[11px] text-muted">
        <span className="text-strong">TERMINAL</span>
        <button type="button" onClick={onClose} aria-label={t.closeTerminal} className="ml-auto h-7 w-[30px] cursor-pointer rounded-md text-base hover:bg-hover">×</button>
      </div>
      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto px-4 pt-0.5 pb-2 leading-[1.7] whitespace-pre-wrap">
        {lines.map((l, i) => (
          <div key={i} style={{ color: l.color }}>
            {l.prompt && <Prompt />}
            {l.t}
          </div>
        ))}
        {typing !== null && (
          <div>
            <Prompt />
            {typing}
            <span className="caret" style={{ width: 7, height: 14, verticalAlign: -2, marginLeft: 0 }} />
          </div>
        )}
        {ready && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              exec(input);
            }}
            className="m-0 flex items-baseline"
          >
            <label htmlFor="termin" className="whitespace-pre">
              <Prompt />
            </label>
            <input
              id="termin"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              aria-label={t.termPh}
              placeholder={t.termPh}
              className="min-w-0 flex-1 border-0 bg-transparent p-0 font-[inherit] text-strong caret-brand outline-none"
            />
          </form>
        )}
      </div>
    </section>
  );
}
