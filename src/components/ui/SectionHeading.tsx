import type { ReactNode } from "react";

type Props = {
  eyebrow?: string;
  title: string;
  intro?: ReactNode;
  align?: "left" | "center";
  tone?: "light" | "dark";
  as?: "h1" | "h2";
  className?: string;
};

export function SectionHeading({ eyebrow, title, intro, align = "left", tone = "light", as = "h2", className = "" }: Props) {
  const Tag = as;
  const alignment = align === "center" ? "mx-auto text-center" : "";
  const titleColour = tone === "dark" ? "text-white" : "text-charcoal";
  const introColour = tone === "dark" ? "text-white/75" : "text-muted";
  const eyebrowColour = tone === "dark" ? "text-brass" : "text-teal";
  return (
    <div className={`max-w-2xl ${alignment} ${className}`}>
      {eyebrow && <p className={`eyebrow ${eyebrowColour}`}>{eyebrow}</p>}
      <Tag className={`mt-3 text-3xl font-bold leading-tight md:text-[2.375rem] ${titleColour}`}>{title}</Tag>
      {intro && <div className={`mt-4 text-lg leading-relaxed ${introColour}`}>{intro}</div>}
    </div>
  );
}
