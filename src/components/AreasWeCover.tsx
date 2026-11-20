import Link from "next/link";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";
import { areaGroups } from "@/content/areas";
import { sections, site } from "@/content/site";

type Props = {
  /** Show the region descriptions (used on the Areas page). */
  detailed?: boolean;
  headingLevel?: "h2" | "h3";
  showHeading?: boolean;
};

export function AreasWeCover({ detailed = false, headingLevel = "h3", showHeading = true }: Props) {
  const RegionHeading = headingLevel;
  const copy = sections.areas;
  return (
    <section id="areas" className="section bg-white">
      <div className="container-site">
        {showHeading && <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} />}
        <div className={`grid gap-8 sm:grid-cols-2 lg:grid-cols-5 ${showHeading ? "mt-12" : ""}`}>
          {areaGroups.map((group) => (
            <div key={group.slug} id={group.slug} className="border-t-2 border-charcoal pt-5">
              <RegionHeading className="font-heading text-[1.0625rem] font-semibold text-charcoal">{group.region}</RegionHeading>
              {detailed && <p className="mt-2 text-sm leading-relaxed text-muted">{group.intro}</p>}
              <ul className="mt-4 space-y-2">
                {group.areas.map((area) => (
                  <li key={area.slug}>
                    {area.published ? (
                      <Link
                        href={`/areas/${area.slug}`}
                        className="text-[0.9375rem] text-ink underline decoration-line underline-offset-4 transition-colors hover:text-teal hover:decoration-teal"
                      >
                        {area.name}
                      </Link>
                    ) : (
                      <span className="text-[0.9375rem] text-ink">{area.name}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col gap-4 rounded-[4px] border border-line bg-ivory p-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[0.9375rem] text-ink">{copy.note}</p>
          <Button href={site.enquiryPath} className="shrink-0">
            {copy.buttonLabel}
          </Button>
        </div>
      </div>
    </section>
  );
}
