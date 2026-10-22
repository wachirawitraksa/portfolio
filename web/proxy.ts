import { NextRequest, NextResponse } from "next/server";

const LANGS = ["th", "en"];

// "/" and any path without a language prefix go to Thai.
export function proxy(req: NextRequest) {
  const first = req.nextUrl.pathname.split("/")[1];
  if (LANGS.includes(first)) return;
  const url = req.nextUrl.clone();
  url.pathname = `/th${req.nextUrl.pathname === "/" ? "" : req.nextUrl.pathname}`;
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/((?!_next|api|favicon.ico|sitemap.xml|robots.txt).*)"] };
