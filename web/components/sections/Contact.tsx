"use client";

import type { Profile } from "../../lib";
import { useShell } from "../shell-context";
import { SectionHead, sectionClass } from "./SectionHead";

export function Contact({ profile }: { profile: Profile | null }) {
  const { t, data, copyEmail, openResume } = useShell();
  const hasCv = Boolean(data.cvTh || data.cvEn);
  const links = profile?.links ?? [];
  const btn = "cursor-pointer rounded-lg px-5 py-[13px] font-mono text-[13px] no-underline transition-shadow hover:shadow-[0_0_0_1px_var(--brand),0_0_18px_rgb(55_148_255/0.3)]";
  const ghost = `${btn} border border-line text-fg hover:text-fg`;

  return (
    <section id="contact" className={`${sectionClass} items-start gap-[18px]`}>
      <SectionHead file="contact.css" title={t.contact} />
      <p className="reveal max-w-[600px] text-lg leading-[1.8]">{t.contactBody}</p>
      <div className="reveal flex flex-wrap gap-3">
        {data.email && <button type="button" onClick={copyEmail} className={`${btn} border-0 bg-brand text-white`}>{t.copyEmail}</button>}
        {data.email && <a href={`mailto:${data.email}`} className={ghost}>{data.email}</a>}
        {links.map((l) => <a key={l.id} href={l.url} target="_blank" rel="noopener" className={ghost}>{l.label} ↗</a>)}
        {hasCv && <button type="button" onClick={openResume} className={ghost}>resume.pdf</button>}
      </div>
    </section>
  );
}
