import Link from "next/link";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";
import { areaGroups } from "@/content/areas";
import { sections, site } from "@/content/site";

type Props = {
  /** Show the region descriptions (used on the Areas page and the home page). */
  detailed?: boolean;
  /** List only the areas that have a published page (home page); the Areas page names every district. */
  publishedOnly?: boolean;
  headingLevel?: "h2" | "h3";
  showHeading?: boolean;
};

export function AreasWeCover({ detailed = false, publishedOnly = false, headingLevel = "h3", showHeading = true }: Props) {
  const RegionHeading = headingLevel;
  const copy = sections.areas;
  const columns = areaGroups.length > 5 ? "lg:grid-cols-3" : "lg:grid-cols-5";
  return (
    <section id="areas" className="section bg-white">
      <div className="container-site">
        {showHeading && <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} />}
        <div className={`grid gap-8 sm:grid-cols-2 ${columns} ${showHeading ? "mt-12" : ""}`}>
          {areaGroups.map((group) => (
            <div key={group.slug} id={group.slug} className="border-t-2 border-charcoal pt-5">
              <RegionHeading className="font-heading text-[1.0625rem] font-semibold text-charcoal">{group.region}</RegionHeading>
              {detailed && <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">{group.intro}</p>}
              <ul className="mt-4 space-y-2">
                {(publishedOnly ? group.areas.filter((a) => a.published) : group.areas).map((area) => (
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
