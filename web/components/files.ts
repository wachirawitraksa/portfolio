import type { SectionId } from "../shell-data";

// Each page section is shown as a "file" in the explorer, the way the mockup does.
export const FILES: Record<SectionId, { name: string; badge: string; color: string }> = {
  home: { name: "home.tsx", badge: "TSX", color: "#4ec9b0" },
  about: { name: "about.md", badge: "MD", color: "#519aba" },
  experience: { name: "career.tsx", badge: "TSX", color: "#4ec9b0" },
  projects: { name: "projects/", badge: "▸", color: "#dcb67a" },
  articles: { name: "articles/", badge: "▸", color: "#dcb67a" },
  skills: { name: "skills.json", badge: "{}", color: "#cbcb41" },
  contact: { name: "contact.css", badge: "#", color: "#569cd6" },
};

export const RESUME_FILE = { name: "resume.pdf", badge: "PDF", color: "#e06c75" };
