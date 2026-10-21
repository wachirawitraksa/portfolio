"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { askQuestion, pick, type AskAnswer } from "../lib";
import { fileInfo, RESUME_FILE } from "./files";
import { useShell } from "./shell-context";

type Line = { t: string; color?: string; prompt?: boolean };
type Entry = { q: string; out: Line[]; answer?: AskAnswer; failed?: boolean; pending: boolean };

type Props = {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  lift: boolean; // the terminal panel is open: sit above it
  request: { id: number; text?: string } | null; // `ask <question>` typed in the terminal
};

const mono = "font-['SF_Mono',Menlo,Monaco,'JetBrains_Mono','IBM_Plex_Sans_Thai',monospace]";

// Shows the answer a few characters at a time, then the sources.
function Reveal({ text, onTick, children }: { text: string; onTick: () => void; children: React.ReactNode }) {
  const [n, setN] = useState(() => (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? text.length : 0));
  useEffect(() => {
    if (n >= text.length) return;
    const id = setTimeout(() => setN((v) => Math.min(text.length, v + 3)), 14);
    return () => clearTimeout(id);
  }, [n, text]);
  useEffect(onTick, [n, onTick]);
  return (
    <>
      <div>{text.slice(0, n)}</div>
      {n >= text.length && children}
    </>
  );
}

export function AskMe({ open, onOpen, onClose, lift, request }: Props) {
  const { lang, t, data, goTo, openResume } = useShell();
  const router = useRouter();
  const [max, setMax] = useState(false);
  const [intro, setIntro] = useState<Line[]>([]);
  const [typing, setTyping] = useState<string | null>(null);
  const [introDone, setIntroDone] = useState(false);
  const [log, setLog] = useState<Entry[]>([]);
  const [input, setInput] = useState("");
  const busy = log.some((e) => e.pending);
  const started = useRef(false);
  const handled = useRef(0);
  const scroller = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const first = (data.slug.replace(/-portfolio$/, "") || "guest").toLowerCase();
  const prompt = `${first}@portfolio ~ % `;
  const suggestions = [t.sug1, t.sug2, t.sug3];

  const toBottom = useCallback(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  // First open: a "Last login" line, then `./ask` is typed and the greeting appears.
  useEffect(() => {
    if (!open || started.current) return;
    started.current = true;
    const d = new Date();
    setIntro([{ t: `Last login: ${d.toDateString().slice(0, 10)} ${d.toTimeString().slice(0, 8)} on ttys001` }]);
    let alive = true;
    (async () => {
      const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
      const cmd = "./ask";
      await wait(350);
      for (let i = 1; i <= cmd.length && alive; i++) {
        setTyping(cmd.slice(0, i));
        await wait(70);
      }
      await wait(200);
      if (!alive) return;
      setTyping(null);
      setIntro((p) => [...p, { t: cmd, prompt: true }, { t: "" }, { t: t.greet, color: "#9bd1ff" }, { t: t.chatHint, color: "#9a9a9a" }, { t: "" }]);
      setIntroDone(true);
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the intro plays once
  }, [open]);

  useEffect(toBottom, [intro, typing, log, introDone, open, toBottom]);
  useEffect(() => {
    if (open && introDone) inputRef.current?.focus();
  }, [open, introDone, busy]);

  const sourceHref = (s: AskAnswer["sources"][number]) => (s.type === "project" ? `/${lang}/projects/${s.id}` : s.type === "article" ? `/${lang}/articles/${s.id}` : null);

  const submit = useCallback(
    async (raw: string) => {
      const q = raw.trim();
      setInput("");
      if (!q || log.some((e) => e.pending)) return;
      const lc = q.toLowerCase();
      const local = (out: Line[]) => setLog((p) => [...p, { q, out, pending: false }]);

      if (lc === "clear") {
        setLog([]);
        setIntro([]);
        return;
      }
      if (lc === "exit") return onClose();
      if (lc === "help") return local([...t.chatHelp.split("\n").map((l) => ({ t: l })), ...suggestions.map((s) => ({ t: `  › ${s}` }))]);
      if (lc === "whoami") return local([{ t: data.name || first }]);
      if (lc === "ls") return local([{ t: [...data.sections.map((id) => fileInfo(id, data).name), ...(data.cvTh || data.cvEn ? [RESUME_FILE.name] : [])].join("   "), color: "#6cb6ff" }]);
      if ((lc === "open resume.pdf" || lc === "cv") && (data.cvTh || data.cvEn)) {
        local([{ t: "opening resume.pdf ..." }]);
        return openResume();
      }
      if (lc.startsWith("sudo")) return local([{ t: `${first} is not in the sudoers file. This incident will be reported.`, color: "#ff6b6b" }]);

      setLog((p) => [...p, { q, out: [], pending: true }]);
      let entry: Partial<Entry>;
      try {
        entry = { answer: await askQuestion(q) };
      } catch {
        entry = { failed: true };
      }
      setLog((p) => p.map((e, i) => (i === p.length - 1 ? { ...e, ...entry, pending: false } : e)));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- suggestions/dictionary change only with the language
    [log, onClose, openResume, data, first, t],
  );

  // `ask <question>` from the terminal panel.
  useEffect(() => {
    if (!request || request.id === handled.current || !open) return;
    handled.current = request.id;
    if (request.text) void submit(request.text);
  }, [request, open, submit]);

  const lights = "size-3 cursor-pointer rounded-full border-[0.5px] border-black/25 p-0 text-[9px] leading-[11px] font-bold text-transparent hover:text-black/60";

  if (!open) {
    return (
      <button
        type="button"
        onClick={onOpen}
        aria-label={t.askBtn}
        className={`group absolute right-3 bottom-[38px] z-[5] flex cursor-pointer items-center gap-2 rounded-full border border-white/10 bg-black px-3.5 py-2.5 text-left font-mono text-white shadow-[0_10px_30px_rgb(0_0_0/0.35)] transition-[transform,bottom] duration-200 hover:-translate-y-[3px] hover:scale-[1.03] sm:right-4 sm:bottom-[46px] sm:w-[132px] sm:flex-col sm:items-start sm:rounded-2xl sm:px-3 sm:py-2.5 ide:right-6 ide:w-[150px] ide:px-3.5 ide:py-3 ${lift ? "sm:bottom-[202px]" : ""}`}
      >
        <span className="hidden items-center gap-1.5 sm:flex">
          <span className="flex gap-1.5" aria-hidden="true">
            <span className="size-[9px] rounded-full bg-[#ff5f57]" />
            <span className="size-[9px] rounded-full bg-[#febc2e]" />
            <span className="size-[9px] rounded-full bg-[#28c840]" />
          </span>
          <span className="ml-1.5 text-[11px] font-bold">ASK Me</span>
        </span>
        <span className="text-[13px]">
          <span className="text-[#c084fc]">&gt;</span> <span className="group-hover:text-[#60a5fa]"><span className="hidden sm:inline">openChat()</span><span className="font-bold sm:hidden">ASK Me</span></span>
        </span>
      </button>
    );
  }

  return (
    <>
      <button type="button" onClick={onClose} aria-label={t.closeChat} className="absolute inset-0 z-[5] cursor-default border-0 bg-transparent" />
      <div
        role="dialog"
        aria-label={t.chatTitle}
        className={`absolute right-3 bottom-[38px] z-[6] flex w-[calc(100%-24px)] max-w-[380px] flex-col overflow-hidden rounded-2xl border border-white/20 bg-[rgb(16_16_16/0.94)] text-[#f2f2f2] shadow-[0_22px_70px_rgb(0_0_0/0.55)] outline outline-1 outline-black/60 backdrop-blur-[18px] transition-[bottom] duration-[250ms] h-[min(360px,calc(100%-120px))] sm:right-4 sm:bottom-[46px] sm:h-[min(400px,calc(100%-110px))] sm:w-[min(480px,calc(100%-32px))] sm:max-w-none sm:rounded-[10px] ide:right-6 ide:w-[min(600px,calc(100%-32px))] ${max ? "sm:!h-[calc(100%-90px)] ide:!w-[min(900px,calc(100%-32px))]" : ""} ${lift ? (max ? "sm:!bottom-[202px] sm:!h-[calc(100%-250px)]" : "sm:!bottom-[202px] sm:!h-[min(400px,calc(100%-260px))]") : ""}`}
      >
        <div className="relative flex h-7 shrink-0 items-center border-b border-[#111] bg-gradient-to-b from-[#3b3b3b] to-[#2f2f2f] px-2.5 font-sans">
          <div className="relative z-[1] flex gap-2">
            <button type="button" onClick={onClose} aria-label={t.closeChat} title={`${t.closeChat} (Esc)`} className={`${lights} bg-[#ff5f57]`}>×</button>
            <button type="button" onClick={onClose} aria-label={t.minChat} title={t.minChat} className={`${lights} bg-[#febc2e]`}>−</button>
            <button type="button" onClick={() => setMax((v) => !v)} aria-label={t.maxChat} title={t.maxChat} className={`${lights} bg-[#28c840]`}>+</button>
          </div>
          <span className="pointer-events-none absolute inset-x-0 flex items-center justify-center gap-1.5 text-[13px] font-semibold text-[#b8b8b8]">
            <svg width="14" height="12" viewBox="0 0 16 13" aria-hidden="true"><path d="M1 2.2C1 1.5 1.5 1 2.2 1h3.6l1.4 1.5h6.6c.7 0 1.2.5 1.2 1.2v7.1c0 .7-.5 1.2-1.2 1.2H2.2c-.7 0-1.2-.5-1.2-1.2z" fill="#7ab6f5" /></svg>
            {first} — -zsh — 80×24
          </span>
        </div>

        <div ref={scroller} className={`min-h-0 flex-1 overflow-y-auto px-2 pt-1.5 pb-2.5 text-[12.5px] leading-normal break-words whitespace-pre-wrap ${mono}`} onClick={() => inputRef.current?.focus()}>
          {intro.map((l, i) => (
            <div key={i} style={{ color: l.color, minHeight: "1.5em" }}>
              {l.prompt && <b className="text-[#f2f2f2]">{prompt}</b>}
              {l.t}
            </div>
          ))}
          {typing !== null && (
            <div>
              <b>{prompt}</b>
              {typing}
              <span className="caret" style={{ width: 7, height: 14, background: "#f2f2f2", verticalAlign: -2, marginLeft: 0 }} />
            </div>
          )}
          {introDone && log.length === 0 && (
            <div className="mb-2 flex flex-col items-start gap-1.5">
              {suggestions.map((s) => (
                <button key={s} type="button" onClick={() => void submit(s)} className="cursor-pointer rounded-md border border-white/20 bg-transparent px-2.5 py-1.5 text-left font-[inherit] text-[#9bd1ff] hover:bg-white/10">
                  › {s}
                </button>
              ))}
            </div>
          )}
          {log.map((m, i) => (
            <div key={i} className="mb-2.5">
              <div><b>{prompt}</b>{m.q}</div>
              {m.out.map((l, j) => <div key={j} style={{ color: l.color }}>{l.t}</div>)}
              {m.pending && (
                <div><span className="text-[#4ade80]">⠿</span> <span className="text-white/55">{t.processing}…</span></div>
              )}
              {m.failed && <div className="text-[#ff6b6b]">{t.askFailed}</div>}
              {m.answer && (
                <Reveal text={m.answer.answer} onTick={toBottom}>
                  {m.answer.sources.length > 0 && (
                    <div className="text-[#9a9a9a]">
                      {t.sources}{" "}
                      {m.answer.sources.map((s, k) => {
                        const href = sourceHref(s);
                        const label = pick(lang, s.title_th, s.title_en) || s.section;
                        const go = () => {
                          if (href) router.push(href);
                          else goTo(s.type === "work" && data.sections.includes("experience") ? "experience" : data.sections.includes("about") ? "about" : "home");
                          onClose();
                        };
                        return (
                          <span key={`${s.type}-${s.id}-${k}`}>
                            {k > 0 && ", "}
                            <button type="button" onClick={go} className="cursor-pointer border-0 bg-transparent p-0 font-[inherit] text-[#6cb6ff] underline">{label}</button>
                          </span>
                        );
                      })}
                    </div>
                  )}
                  {m.answer.contact_email && (m.answer.mode === "no_answer" || m.answer.mode === "fallback" || m.answer.mode === "uncertain") && (
                    <div className="text-[#9a9a9a]">{t.contactByEmail} <a href={`mailto:${m.answer.contact_email}`} className="text-[#6cb6ff] underline">{m.answer.contact_email}</a></div>
                  )}
                </Reveal>
              )}
            </div>
          ))}
          {introDone && !busy && (
            <form onSubmit={(e) => { e.preventDefault(); void submit(input); }} className="m-0 flex items-baseline">
              <label htmlFor="ask" className="font-bold whitespace-pre">{prompt}</label>
              <input
                id="ask"
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                maxLength={1000}
                autoComplete="off"
                spellCheck={false}
                aria-label={t.askPh}
                className="min-w-0 flex-1 border-0 bg-transparent p-0 font-[inherit] text-[#f2f2f2] caret-[#f2f2f2] outline-none"
              />
            </form>
          )}
        </div>
      </div>
    </>
  );
}
