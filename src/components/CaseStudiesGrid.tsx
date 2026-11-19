"use client";

import { useMemo, useState } from "react";
import { CaseStudyCard } from "@/components/CaseStudyCard";
import type { CaseStudy } from "@/content/case-studies";

/** The case-study grid with category filter buttons (the categories come from the entries themselves). */
export function CaseStudiesGrid({ studies, headingLevel = "h2" }: { studies: CaseStudy[]; headingLevel?: "h2" | "h3" }) {
  const categories = useMemo(() => ["All", ...Array.from(new Set(studies.map((s) => s.category)))], [studies]);
  const [category, setCategory] = useState("All");
  const filtered = category === "All" ? studies : studies.filter((s) => s.category === category);

  return (
    <div>
      {categories.length > 2 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter case studies by type">
          {categories.map((cat) => {
            const active = cat === category;
            return (
              <button
                key={cat}
                type="button"
                aria-pressed={active}
                onClick={() => setCategory(cat)}
                className={`rounded-[4px] border px-4 py-2 font-heading text-sm font-semibold transition-colors ${
                  active ? "border-charcoal bg-charcoal text-white" : "border-line bg-white text-charcoal hover:border-teal hover:text-teal"
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>
      )}
      <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3" aria-live="polite">
        {filtered.map((s) => (
          <li key={s.slug}>
            <CaseStudyCard study={s} headingLevel={headingLevel} />
          </li>
        ))}
      </ul>
      {filtered.length === 0 && <p className="mt-8 text-muted">No case studies in this category yet.</p>}
    </div>
  );
}
