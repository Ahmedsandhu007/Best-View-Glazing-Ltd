import type { Metadata } from "next";
import Image from "next/image";
import { PageHeader } from "@/components/ui/PageHeader";
import { AreasWeCover } from "@/components/AreasWeCover";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { images } from "@/content/images";
import { pages, seo, site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: seo.areas.title,
  description: seo.areas.description,
  alternates: { canonical: "/areas" },
  openGraph: { title: `${seo.areas.title} | ${site.name}`, url: "/areas" },
};

export default function AreasPage() {
  const copy = pages.areas;
  return (
    <>
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} crumbs={[{ label: "Areas We Cover" }]} />
      <section className="section bg-white">
        <div className="container-site grid items-center gap-10 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            <h2 className="text-2xl font-bold md:text-3xl">{copy.bodyTitle}</h2>
            <div className="prose-site mt-5 text-[1.0625rem] leading-relaxed text-ink">
              {copy.paragraphs.map((p) => (
                <p key={p.slice(0, 40)}>{p}</p>
              ))}
            </div>
          </div>
          <div className="lg:col-span-5">
            <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
              <Image src={images.areas.src} alt={images.areas.alt} fill priority sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
            </div>
          </div>
        </div>
      </section>
      <div className="border-t border-line">
        <AreasWeCover detailed headingLevel="h2" showHeading={false} />
      </div>
      <CtaBand />
      <JsonLd data={breadcrumbJsonLd([{ name: "Areas We Cover", path: "/areas" }])} />
    </>
  );
}
