import Image from "next/image";
import Link from "next/link";
import { ArrowRight, MapPin } from "lucide-react";
import type { CaseStudy } from "@/content/case-studies";

export function CaseStudyCard({ study, headingLevel = "h3" }: { study: CaseStudy; headingLevel?: "h2" | "h3" }) {
  const Heading = headingLevel;
  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-[4px] border border-line bg-white transition-colors hover:border-teal/50 focus-within:border-teal">
      <div className="relative aspect-[4/3] overflow-hidden border-b border-line bg-ivory">
        <Image
          src={study.image}
          alt={study.imageAlt}
          fill
          loading="lazy"
          sizes="(min-width: 1024px) 380px, (min-width: 640px) 50vw, 100vw"
          className="object-cover transition-transform duration-300 group-hover:scale-[1.02]"
        />
        <span className="absolute left-3 top-3 rounded-[3px] bg-charcoal/90 px-2.5 py-1 font-heading text-xs font-semibold text-white">{study.category}</span>
      </div>
      <div className="flex flex-1 flex-col p-6">
        <Heading className="font-heading text-[1.125rem] font-semibold leading-snug text-charcoal">
          <Link href={`/case-studies/${study.slug}`} className="after:absolute after:inset-0 after:content-[''] group-hover:text-teal focus-visible:outline-none">
            {study.title}
          </Link>
        </Heading>
        <p className="mt-1.5 inline-flex items-center gap-1.5 text-sm text-muted">
          <MapPin className="h-3.5 w-3.5" aria-hidden="true" /> {study.location}
        </p>
        <p className="mt-2.5 text-[0.9375rem] leading-relaxed text-muted">{study.excerpt}</p>
        {study.results.length > 0 && (
          <dl className="mt-5 grid grid-cols-3 gap-2 border-t border-line pt-4">
            {study.results.slice(0, 3).map((r) => (
              <div key={r.label}>
                <dt className="text-[0.7rem] uppercase tracking-[0.08em] text-muted">{r.label}</dt>
                <dd className="font-heading text-lg font-bold text-charcoal">{r.value}</dd>
              </div>
            ))}
          </dl>
        )}
        <span className="mt-auto inline-flex items-center gap-1.5 pt-5 font-heading text-sm font-semibold text-teal">
          Read the case study
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </span>
      </div>
    </article>
  );
}
