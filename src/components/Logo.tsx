import Link from "next/link";
import { site } from "@/content/site";

type LogoProps = {
  /** "dark" renders charcoal text for light backgrounds; "light" renders white text. */
  variant?: "dark" | "light";
  className?: string;
  asLink?: boolean;
};

/** Geometric window-frame mark. Used in the header, footer, favicon and social image. */
export function LogoMark({ className = "h-9 w-9", accent = "#C5A477" }: { className?: string; accent?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true" focusable="false">
      <rect x="2.25" y="2.25" width="35.5" height="35.5" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <path d="M20 2.25v35.5M2.25 20h35.5" fill="none" stroke="currentColor" strokeWidth="2" />
      <rect x="23.5" y="23.5" width="11" height="11" fill={accent} />
    </svg>
  );
}

export function Logo({ variant = "dark", className = "", asLink = true }: LogoProps) {
  const text = variant === "dark" ? "text-charcoal" : "text-white";
  const sub = variant === "dark" ? "text-muted" : "text-white/70";
  const content = (
    <span className={`inline-flex items-center gap-3 ${text} ${className}`}>
      <LogoMark />
      <span className="flex flex-col leading-none">
        <span className="font-heading text-[1.2rem] font-bold tracking-tight">Best View</span>
        <span className={`mt-1 font-heading text-[0.66rem] font-semibold uppercase tracking-[0.16em] ${sub}`}>
          Glazing Ltd
        </span>
      </span>
    </span>
  );
  if (!asLink) return content;
  return (
    <Link href="/" title={`${site.name} – home`} className="inline-flex shrink-0 rounded-sm">
      {content}
    </Link>
  );
}
