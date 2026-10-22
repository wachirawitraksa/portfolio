"use client";

import { useEffect, useState } from "react";
import type { Profile } from "../../lib";
import { imageSrcSet, imageUrl, pick } from "../../lib";
import { useShell } from "../shell-context";

// Types the text out, holds, then erases, like the mockup's `const role = "..."` line.
function Typewriter({ text }: { text: string }) {
  const [n, setN] = useState(text.length);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let i = 0;
    let dir = 1;
    let hold = 0;
    setN(0);
    const id = setInterval(() => {
      if (hold > 0) return void hold--;
      i += dir;
      setN(i);
      if (i >= text.length) { dir = -1; hold = 14; }
      else if (i <= 0) { dir = 1; hold = 4; }
    }, 90);
    return () => clearInterval(id);
  }, [text]);
  return (
    <>
      <span aria-hidden="true">{text.slice(0, n)}</span>
      <span className="sr-only">{text}</span>
    </>
  );
}

export function Hero({ profile, role }: { profile: Profile | null; role: string }) {
  const { lang, t, data, goTo, openResume } = useShell();
  const name = profile ? pick(lang, profile.name_th, profile.name_en) : "";
  const location = profile ? pick(lang, profile.location_th, profile.location_en) : "";
  const hasCv = Boolean(data.cvTh || data.cvEn);
  const firstKind = data.kinds[0]?.id;

  return (
    <section id="home" className="flex min-h-[min(520px,70vh)] flex-col items-start gap-7 pt-8 ide:flex-row ide:items-center ide:gap-14">
      {profile?.photo_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageUrl(profile.photo_url, 640)} srcSet={imageSrcSet(profile.photo_url, [320, 640, 960])} sizes="(min-width: 901px) 300px, (min-width: 640px) 200px, 120px" alt={name} className="order-first size-[120px] shrink-0 rounded-[20px] bg-card object-cover sm:size-[200px] ide:order-last ide:aspect-[4/5] ide:h-auto ide:w-[300px]" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-5">
        {role && (
          <div className="font-mono text-[15px]">
            <span className="text-kw">const</span> <span className="text-type">role</span> = <span className="text-str">&quot;<Typewriter text={role} />&quot;</span>
            <span className="caret" />
          </div>
        )}
        <h1 className="text-[clamp(38px,6vw,68px)] leading-[1.08] font-bold tracking-tight text-strong [overflow-wrap:anywhere]">{name || t.empty}</h1>
        {location && <p className="font-mono text-sm text-muted">{location}</p>}
        <div className="mt-1 flex flex-wrap gap-3">
          {firstKind && (
            <button type="button" onClick={() => goTo(firstKind)} className="cursor-pointer rounded-lg bg-brand px-[22px] py-[13px] font-mono text-[13px] text-white transition-shadow hover:shadow-[0_0_0_1px_var(--brand),0_0_18px_rgb(55_148_255/0.3)]">
              {t.seeWork}
            </button>
          )}
          {hasCv && (
            <button type="button" onClick={openResume} className="cursor-pointer rounded-md border border-line px-[22px] py-[13px] font-mono text-[13px] hover:bg-hover">
              resume.pdf
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
