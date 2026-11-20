import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { QuoteSection } from "@/components/QuoteSection";
import { JsonLd } from "@/components/JsonLd";
import { areaGroups, findArea, publishedAreas } from "@/content/areas";
import { services } from "@/content/services";
import { site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

type Params = { slug: string };

export function generateStaticParams(): Params[] {
  return publishedAreas.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const area = findArea(slug);
  if (!area) return {};
  const path = `/areas/${area.slug}`;
  return {
    title: `Window & Door Repairs ${area.name}`,
    description: `uPVC, aluminium, timber and sash window repairs, double glazing, locks, hinges and door repairs in ${area.name}, ${area.region}. Residential and commercial. Request a free quote.`,
    alternates: { canonical: path },
    openGraph: { title: `Window & Door Repairs ${area.name} | ${site.name}`, url: path },
  };
}

export default async function AreaPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const area = findArea(slug);
  if (!area) notFound();
  const group = areaGroups.find((g) => g.slug === area.regionSlug)!;
  const neighbours = group.areas.filter((a) => a.published === true && a.slug !== area.slug);

  return (
    <>
      <PageHeader
        eyebrow={area.region}
        title={`Window & Door Repairs in ${area.name}`}
        intro={`Repairs to uPVC, aluminium, timber and sash windows, double glazing, locks, handles, hinges and door mechanisms for homes and commercial premises in ${area.name} and the surrounding parts of ${area.region}.`}
        crumbs={[{ label: "Areas We Cover", href: "/areas" }, { label: area.name }]}
      >
        <Button href={`#${site.enquiryFormId}`} variant="light" size="lg">
          Request a Free Quote
        </Button>
      </PageHeader>

      <section className="section bg-white">
        <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            <h2 className="text-2xl font-bold md:text-3xl">Window and door repairs for {area.name} properties</h2>
            <div className="prose-site mt-5 text-[1.0625rem] leading-relaxed text-ink">
              <p>
                {area.name} sits within our {area.region} coverage. {group.intro}
              </p>
              <p>
                Whatever the age or style of the property, the faults tend to be familiar: windows that have dropped on worn
                hinges, handles and locks that no longer engage, sealed units that have misted, sashes that stick or rattle,
                and doors that need lifting to lock. We diagnose the cause, propose a practical repair and quote for it clearly
                before any work is agreed.
              </p>
              <p>
                We work for homeowners, tenants and landlords in {area.name} as well as for letting agents, property managers
                and commercial occupiers. Enquiries are made through the website form, which lets you attach photographs of the
                problem and tell us when you would prefer to be contacted.
              </p>
            </div>

            <h2 className="mt-12 text-2xl font-bold md:text-3xl">Services available in {area.name}</h2>
            <ul className="mt-5 grid gap-x-8 gap-y-2.5 sm:grid-cols-2">
              {services.map((s) => (
                <li key={s.slug}>
                  <Link
                    href={`/services/${s.slug}`}
                    className="inline-flex items-center gap-2 text-[0.9375rem] font-medium text-charcoal underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal"
                  >
                    {s.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <aside className="lg:col-span-5">
            <div className="rounded-[4px] border border-line bg-ivory p-6">
              <h2 className="font-heading text-lg font-semibold text-charcoal">Other areas in {area.region}</h2>
              {neighbours.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {neighbours.map((n) => (
                    <li key={n.slug}>
                      <Link href={`/areas/${n.slug}`} className="text-[0.9375rem] text-ink underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal">
                        Window &amp; door repairs in {n.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              <Link href="/areas" className="mt-5 inline-flex items-center gap-1.5 font-heading text-[0.9375rem] font-semibold text-teal">
                All London areas
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-6 rounded-[4px] border border-line bg-white p-6">
              <h2 className="font-heading text-lg font-semibold text-charcoal">No local branch, no middleman</h2>
              <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">
                We do not have an office in {area.name}; every enquiry is handled by our central team and the repair is carried
                out at your property.
              </p>
            </div>
          </aside>
        </div>
      </section>

      <QuoteSection />
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Areas We Cover", path: "/areas" },
          { name: area.name, path: `/areas/${area.slug}` },
        ])}
      />
    </>
  );
}
