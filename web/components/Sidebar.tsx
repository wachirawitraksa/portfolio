"use client";

import { useEffect, useState } from "react";
import { timeAgo } from "../format";
import type { Dict } from "../i18n";
import type { Lang } from "../lib";
import type { SectionId, ShellData, UpdateRow } from "../shell-data";
import type { OutlineItem } from "./shell-context";
import { fileInfo, RESUME_FILE } from "./files";

type Props = {
  lang: Lang;
  data: ShellData;
  t: Dict;
  active: SectionId | null;
  pageOutline: OutlineItem[] | null;
  hasCv: boolean;
  className: string;
  goTo: (id: SectionId) => void;
  openResume: () => void;
  onChat: () => void;
  onUpdate: (update: UpdateRow) => void;
};

function Chevron({ open }: { open: boolean }) {
  return <span className={`inline-block w-3 transition-transform ${open ? "rotate-90" : ""}`}>›</span>;
}

const UPDATE_COLOR: Record<UpdateRow["type"], string> = { project: "#4ec9b0", article: "#dcb67a", work: "#569cd6", education: "#519aba", profile: "#9a9a9a" };

export function Sidebar({ lang, data, t, active, pageOutline, hasCv, className, goTo, openResume, onChat, onUpdate }: Props) {
  const [filesOpen, setFilesOpen] = useState(true);
  const [timelineOpen, setTimelineOpen] = useState(false);
  // Relative times use the clock, so they appear after mount; the server and first browser render agree on none.
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => setNow(Date.now()), []);
  const [outlineToggled, setOutlineOpen] = useState<boolean | null>(null);
  // Closed on the home page like the mockup; a detail page opens it because its headings are the point.
  const outlineOpen = outlineToggled ?? Boolean(pageOutline);

  const row = "flex w-full items-center gap-2 rounded-none px-3 py-[5px] text-left text-[13px] text-fg hover:bg-hover";
  type Row = { label: string; id: string; pad: number; sub?: string; page?: boolean };
  const outline: Row[] = [];
  // On a detail page the outline lists that page's own headings instead of the home sections.
  for (const item of pageOutline ?? []) outline.push({ label: item.label, id: item.id, pad: 14, page: true });
  for (const id of pageOutline ? [] : data.sections) {
    const kind = data.kinds.find((k) => k.id === id);
    const label = kind ? kind.title : id === "home" ? "home" : id === "experience" ? t.career : id === "contact" ? t.contact : id === "about" ? t.about : id === "education" ? t.education : id === "how" ? t.howIWork : id === "articles" ? t.articles : t.skills;
    outline.push({ label, id, pad: 14, sub: kind ? String(kind.count) : undefined });
    if (id === "experience") for (const job of data.jobs) outline.push({ label: job, id, pad: 30 });
  }

  return (
    <aside aria-label={t.explorer} className={`${className} w-[220px] shrink-0 flex-col border-r border-line bg-side text-[13px]`}>
      <div className="px-4 pt-3 pb-1.5 font-mono text-[11px] tracking-[0.08em] text-muted">EXPLORER</div>
      <button
        type="button"
        onClick={() => setFilesOpen(!filesOpen)}
        aria-expanded={filesOpen}
        className="flex h-[26px] items-center gap-1.5 px-2.5 text-left font-mono text-[11px] font-bold tracking-[0.06em] text-strong hover:bg-hover"
      >
        <Chevron open={filesOpen} />
        {data.slug.toUpperCase()}
      </button>
      {filesOpen && (
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          {data.sections.map((id) => {
            const f = fileInfo(id, data);
            const on = id === active;
            return (
              <button
                key={id}
                type="button"
                onClick={() => goTo(id)}
                aria-current={on ? "true" : undefined}
                className={`flex items-center gap-2.5 border-l-2 px-4 py-[7px] text-left font-mono text-[13px] hover:bg-hover ${on ? "border-brand bg-sel text-strong" : "border-transparent text-fg"}`}
              >
                <span className="w-6 text-[10px] font-bold" style={{ color: f.color }}>{f.badge}</span>
                {f.name}
              </button>
            );
          })}
          {hasCv && (
            <button type="button" onClick={openResume} className="flex items-center gap-2.5 border-l-2 border-transparent px-4 py-[7px] text-left font-mono text-[13px] text-fg hover:bg-hover">
              <span className="w-6 text-[10px] font-bold" style={{ color: RESUME_FILE.color }}>{RESUME_FILE.badge}</span>
              {RESUME_FILE.name}
            </button>
          )}
        </div>
      )}
      <div className="mt-auto flex max-h-[60%] min-h-0 flex-col">
        <div className="flex min-h-0 flex-col border-t border-line">
          <button
            type="button"
            onClick={() => setOutlineOpen(!outlineOpen)}
            aria-expanded={outlineOpen}
            className="flex h-7 shrink-0 items-center gap-1.5 px-2.5 text-left font-mono text-[11px] font-bold tracking-[0.06em] text-fg hover:bg-hover"
          >
            <Chevron open={outlineOpen} />
            OUTLINE
          </button>
          {outlineOpen && (
            <div className="max-h-[200px] overflow-y-auto pb-1.5">
              {outline.map((o, i) => (
                <button key={`${o.id}-${i}`} type="button" onClick={() => (o.page ? document.getElementById(o.id)?.scrollIntoView({ behavior: "smooth", block: "start" }) : goTo(o.id as SectionId))} className={row} style={{ paddingLeft: o.pad }}>
                  <span className="w-4 shrink-0 font-mono text-[11px] font-bold" style={{ color: o.pad === 14 && !o.page ? "#b180d7" : "#75beff" }}>{o.pad === 14 && !o.page ? "◆" : "▪"}</span>
                  <span className="min-w-0 flex-1 truncate">{o.label}</span>
                  {o.sub && <span className="font-mono text-[11px] text-muted">{o.sub}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
        {data.updates.length > 0 && (
          <div className="flex min-h-0 flex-col border-t border-line">
            <button
              type="button"
              onClick={() => setTimelineOpen(!timelineOpen)}
              aria-expanded={timelineOpen}
              className="flex h-7 shrink-0 items-center gap-1.5 px-2.5 text-left font-mono text-[11px] font-bold tracking-[0.06em] text-fg hover:bg-hover"
            >
              <Chevron open={timelineOpen} />
              TIMELINE
            </button>
            {timelineOpen && (
              <div className="max-h-[200px] overflow-y-auto pb-1.5">
                {data.updates.map((u) => (
                  <button key={`${u.type}-${u.id}`} type="button" onClick={() => onUpdate(u)} className={row} style={{ paddingLeft: 14 }}>
                    <span className="w-4 shrink-0 font-mono text-[11px] font-bold" style={{ color: UPDATE_COLOR[u.type] }}>●</span>
                    <span className="min-w-0 flex-1 truncate">{u.label}</span>
                    <span className="font-mono text-[11px] whitespace-nowrap text-muted">{now ? timeAgo(u.at, lang, now) : ""}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="flex flex-col gap-2 border-t border-line p-3 sm:hidden">
        <button type="button" onClick={onChat} className="cursor-pointer rounded-md border border-line px-3 py-2.5 text-left font-mono text-[13px] text-fg hover:bg-hover">&gt; openChat()</button>
        {data.github && <a href={data.github} target="_blank" rel="noopener" className="rounded-md border border-line px-3 py-2.5 font-mono text-[13px] text-fg no-underline">GitHub ↗</a>}
      </div>
    </aside>
  );
}
