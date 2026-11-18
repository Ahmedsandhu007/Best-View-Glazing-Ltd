import type { Metadata } from "next";
import Image from "next/image";
import { PageHeader } from "@/components/ui/PageHeader";
import { AreasWeCover } from "@/components/AreasWeCover";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { images } from "@/content/images";
import { site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Areas We Cover – Window Repairs Throughout London",
  description:
    "Window and door repairs across Greater London: Central, North, East, South and West London including Westminster, Islington, Stratford, Croydon, Hammersmith and more.",
  alternates: { canonical: "/areas" },
  openGraph: { title: `Areas We Cover | ${site.name}`, url: "/areas" },
};

export default function AreasPage() {
  return (
    <>
      <PageHeader
        eyebrow="Areas we cover"
        title="Window & Door Repairs Throughout London"
        intro="We serve residential and commercial customers across Greater London. Every enquiry is handled by the same central team and the repair is carried out at your property, so the service is consistent whichever part of the capital you are in."
        crumbs={[{ label: "Areas We Cover" }]}
      />
      <section className="section bg-white">
        <div className="container-site grid items-center gap-10 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            <h2 className="text-2xl font-bold md:text-3xl">London-wide, not a single borough</h2>
            <div className="prose-site mt-5 text-[1.0625rem] leading-relaxed text-ink">
              <p>
                London’s housing and commercial stock varies enormously from one district to the next: Georgian and Victorian
                sash windows in the centre and inner suburbs, inter-war timber and steel casements further out, decades of
                uPVC replacements, and aluminium and tilt and turn systems in flats and offices. We repair all of them.
              </p>
              <p>
                The districts listed below are those we are asked to attend most often. They are not an exhaustive list and we
                do not operate branch offices in them. If your property is anywhere within Greater London, please send an
                enquiry and we will confirm that we can help.
              </p>
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
