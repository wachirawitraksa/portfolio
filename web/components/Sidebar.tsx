"use client";

import { useState } from "react";
import type { Dict } from "../i18n";
import type { SectionId, ShellData } from "../shell-data";
import { FILES, RESUME_FILE } from "./files";

type Props = {
  data: ShellData;
  t: Dict;
  active: SectionId;
  hasCv: boolean;
  className: string;
  goTo: (id: SectionId) => void;
  openResume: () => void;
};

function Chevron({ open }: { open: boolean }) {
  return <span className={`inline-block w-3 transition-transform ${open ? "rotate-90" : ""}`}>›</span>;
}

export function Sidebar({ data, t, active, hasCv, className, goTo, openResume }: Props) {
  const [filesOpen, setFilesOpen] = useState(true);
  const [outlineOpen, setOutlineOpen] = useState(false);

  const row = "flex w-full items-center gap-2 rounded-none px-3 py-[5px] text-left text-[13px] text-fg hover:bg-hover";
  const outline: { label: string; id: SectionId; pad: number; sub?: string }[] = [];
  for (const id of data.sections) {
    const label = id === "home" ? "home" : id === "experience" ? t.career : id === "contact" ? t.contact : t[id];
    outline.push({ label, id, pad: 14, sub: id === "projects" ? String(data.projectCount) : undefined });
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
            const f = FILES[id];
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
                <button key={`${o.id}-${i}`} type="button" onClick={() => goTo(o.id)} className={row} style={{ paddingLeft: o.pad }}>
                  <span className="w-4 shrink-0 font-mono text-[11px] font-bold" style={{ color: o.pad === 14 ? "#b180d7" : "#75beff" }}>{o.pad === 14 ? "◆" : "▪"}</span>
                  <span className="min-w-0 flex-1 truncate">{o.label}</span>
                  {o.sub && <span className="font-mono text-[11px] text-muted">{o.sub}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      {data.github && (
        <div className="flex flex-col gap-2 border-t border-line p-3 sm:hidden">
          <a href={data.github} target="_blank" rel="noopener" className="rounded-md border border-line px-3 py-2.5 font-mono text-[13px] text-fg no-underline">GitHub ↗</a>
        </div>
      )}
    </aside>
  );
}
