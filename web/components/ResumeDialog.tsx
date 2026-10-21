"use client";

import type { Dict } from "../i18n";
import type { ShellData } from "../shell-data";

export function ResumeDialog({ data, t, onClose }: { data: ShellData; t: Dict; onClose: () => void }) {
  const btn = "rounded-md px-4 py-[11px] font-mono text-[13px] no-underline";
  return (
    <div className="absolute inset-0 z-[8] flex items-center justify-center p-4">
      <button type="button" onClick={onClose} aria-label={t.close} className="absolute inset-0 cursor-default border-0 bg-scrim" />
      <div role="dialog" aria-label="resume.pdf" className="relative w-[min(440px,100%)] overflow-hidden rounded-2xl border border-white/10 bg-black font-mono text-white shadow-2xl">
        <div className="flex h-[34px] items-center gap-2 bg-[#2d2d2d] px-3">
          <button type="button" onClick={onClose} aria-label={t.close} className="size-3.5 cursor-pointer rounded-full border-0 bg-[#ff5f57] p-0" />
          <span className="flex-1 text-center text-xs text-[#c8c8c8]">resume.pdf</span>
        </div>
        <div className="flex flex-col gap-3 p-5 text-[13px]">
          <div><b>{data.slug}</b> ~ % open resume.pdf</div>
          <div className="text-[#a3a3a3]">{t.resumeHint}</div>
          <div className="mt-1 flex flex-wrap gap-2.5">
            {data.cvTh && <a href={data.cvTh} download className={`${btn} bg-[#3794ff] text-white`}>CV ภาษาไทย</a>}
            {data.cvEn && <a href={data.cvEn} download className={`${btn} border border-white/30 text-white`}>CV English</a>}
          </div>
        </div>
      </div>
    </div>
  );
}
