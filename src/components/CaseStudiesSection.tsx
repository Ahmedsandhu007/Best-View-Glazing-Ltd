import { SectionHeading } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";
import { CaseStudyCard } from "@/components/CaseStudyCard";
import { caseStudies, hasPlaceholderCaseStudies } from "@/content/case-studies";
import { sections } from "@/content/site";

/** Home page: the first three case studies. */
export function CaseStudiesSection() {
  const copy = sections.caseStudies;
  const featured = caseStudies.slice(0, 3);
  if (featured.length === 0) return null;
  return (
    <section className="section bg-ivory">
      <div className="container-site">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} />
          <Button href="/case-studies" variant="secondary" className="shrink-0">
            {copy.buttonLabel}
          </Button>
        </div>
        {hasPlaceholderCaseStudies && (
          <p className="mt-6 inline-block rounded-[4px] border border-brass/60 bg-white px-3 py-1.5 text-sm text-ink">{copy.placeholderNotice}</p>
        )}
        <ul className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {featured.map((s) => (
            <li key={s.slug}>
              <CaseStudyCard study={s} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
