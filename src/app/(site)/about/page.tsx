import type { Metadata } from "next";
import Image from "next/image";
import { PageHeader } from "@/components/ui/PageHeader";
import { WhyChooseUs } from "@/components/WhyChooseUs";
import { WorkingProcess } from "@/components/WorkingProcess";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { images } from "@/content/images";
import { pages, seo, site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: seo.about.title,
  description: seo.about.description,
  alternates: { canonical: "/about" },
  openGraph: { title: `${seo.about.title} | ${site.name}`, url: "/about" },
};

export default function AboutPage() {
  const about = pages.about;
  return (
    <>
      <PageHeader eyebrow={about.eyebrow} title={about.title} intro={about.description} crumbs={[{ label: "About Us" }]} />

      <section className="section bg-white">
        <div className="container-site grid items-start gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            <h2 className="text-3xl font-bold leading-tight md:text-[2.375rem]">{about.bodyTitle}</h2>
            <div className="prose-site mt-6 text-[1.0625rem] leading-relaxed text-ink">
              {about.paragraphs.map((p) => (
                <p key={p.slice(0, 40)}>{p}</p>
              ))}
            </div>
          </div>
          <div className="lg:col-span-5">
            <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
              <Image src={images.about.src} alt={images.about.alt} fill priority sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <figure>
                <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
                  <Image src={images.workshop.src} alt={images.workshop.alt} fill loading="lazy" sizes="(min-width: 1024px) 220px, 50vw" className="object-cover" />
                </div>
                <figcaption className="mt-2 text-sm text-muted">{about.captionOne}</figcaption>
              </figure>
              <figure>
                <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
                  <Image
                    src={images.commercialExterior.src}
                    alt={images.commercialExterior.alt}
                    fill
                    loading="lazy"
                    sizes="(min-width: 1024px) 220px, 50vw"
                    className="object-cover"
                  />
                </div>
                <figcaption className="mt-2 text-sm text-muted">{about.captionTwo}</figcaption>
              </figure>
            </div>
          </div>
        </div>
      </section>

      {about.facts.length > 0 && (
        <section className="border-y border-line bg-ivory">
          <div className="container-site grid gap-8 py-12 md:grid-cols-3">
            {about.facts.map((item) => (
              <div key={item.title} className="border-l-2 border-brass pl-5">
                <h2 className="font-heading text-lg font-semibold text-charcoal">{item.title}</h2>
                <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">{item.text}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <WhyChooseUs ctaHref={site.enquiryPath} />
      <WorkingProcess />
      <CtaBand />
      <JsonLd data={breadcrumbJsonLd([{ name: "About Us", path: "/about" }])} />
    </>
  );
}
