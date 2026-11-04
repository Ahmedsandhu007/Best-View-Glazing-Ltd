import type { Metadata } from "next";
import Image from "next/image";
import { PageHeader } from "@/components/ui/PageHeader";
import { WhyChooseUs } from "@/components/WhyChooseUs";
import { WorkingProcess } from "@/components/WorkingProcess";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { images } from "@/content/images";
import { site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "About Us – Window & Door Repair Specialists London",
  description:
    "Best View Glazing Ltd is a London window and door repair specialist serving homeowners, tenants, landlords, letting agents, property managers and commercial premises.",
  alternates: { canonical: "/about" },
  openGraph: { title: `About Us | ${site.name}`, url: "/about" },
};

export default function AboutPage() {
  return (
    <>
      <PageHeader
        eyebrow="About us"
        title="A repair business, not a replacement sales team"
        intro="Best View Glazing Ltd exists to keep the windows and doors London already has working properly, securely and for longer."
        crumbs={[{ label: "About Us" }]}
      />

      <section className="section bg-white">
        <div className="container-site grid items-start gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            <h2 className="text-3xl font-bold leading-tight md:text-[2.375rem]">Who we are and how we work</h2>
            <div className="prose-site mt-6 text-[1.0625rem] leading-relaxed text-ink">
              <p>
                We are a specialist window and door repair company operating across Greater London. Our work is focused on the
                faults that stop windows and doors doing their job: failed hinges, handles and locks, misted or broken sealed
                units, dropped sashes, perished seals and damaged frames.
              </p>
              <p>
                Because we repair rather than sell new windows, our advice starts from the assumption that what you already
                have can be put right. Most of the time it can. When it cannot, or when a repair would not be good value, we
                say so and explain why.
              </p>
              <p>
                We work for private homeowners and tenants, for landlords and letting agencies managing multiple properties,
                for property management companies responsible for blocks and estates, and for commercial occupiers including
                offices and retail businesses. Each type of customer has different needs around access, timing and
                paperwork, and we plan the work accordingly.
              </p>
              <p>
                Every enquiry comes through the website form, is reviewed by someone who understands window and door
                hardware, and is answered with a clear written quotation. It is a simple process and we keep it that way.
              </p>
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
                <figcaption className="mt-2 text-sm text-muted">Hardware, joinery and glazing repairs</figcaption>
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
                <figcaption className="mt-2 text-sm text-muted">Residential and commercial premises</figcaption>
              </figure>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-line bg-ivory">
        <div className="container-site grid gap-8 py-12 md:grid-cols-3">
          {[
            { title: "Who we help", text: "Homeowners, tenants, landlords, letting agencies, property management companies, offices and retail businesses." },
            { title: "What we repair", text: "uPVC, aluminium, timber and sash windows, tilt and turn units, double glazing, and the locks, hinges and mechanisms on doors." },
            { title: "Where we work", text: "Throughout Greater London, from Westminster and Camden to Croydon, Romford, Harrow and Richmond." },
          ].map((item) => (
            <div key={item.title} className="border-l-2 border-brass pl-5">
              <h2 className="font-heading text-lg font-semibold text-charcoal">{item.title}</h2>
              <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      <WhyChooseUs ctaHref={site.enquiryPath} />
      <WorkingProcess />
      <CtaBand />
      <JsonLd data={breadcrumbJsonLd([{ name: "About Us", path: "/about" }])} />
    </>
  );
}
