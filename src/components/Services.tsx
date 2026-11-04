import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";
import { images } from "@/content/images";
import { services, type Service } from "@/content/services";

export function ServiceCard({ service, headingLevel = "h3" }: { service: Service; headingLevel?: "h2" | "h3" }) {
  const img = images[service.image];
  const Heading = headingLevel;
  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-[4px] border border-line bg-white transition-colors hover:border-teal/50 focus-within:border-teal">
      <div className="relative aspect-[16/10] overflow-hidden border-b border-line bg-ivory">
        <Image
          src={img.src}
          alt={img.alt}
          fill
          loading="lazy"
          sizes="(min-width: 1024px) 380px, (min-width: 640px) 50vw, 100vw"
          className="object-cover transition-transform duration-300 group-hover:scale-[1.02]"
        />
      </div>
      <div className="flex flex-1 flex-col p-6">
        <Heading className="font-heading text-[1.125rem] font-semibold leading-snug text-charcoal">
          <Link href={`/services/${service.slug}`} className="after:absolute after:inset-0 after:content-[''] group-hover:text-teal focus-visible:outline-none">
            {service.title}
          </Link>
        </Heading>
        <p className="mt-2.5 text-[0.9375rem] leading-relaxed text-muted">{service.summary}</p>
        <span className="mt-auto inline-flex items-center gap-1.5 pt-5 font-heading text-sm font-semibold text-teal">
          Learn more
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </span>
      </div>
    </article>
  );
}

type Props = {
  /** Render without the section heading (used on the services page under its own H1). */
  compact?: boolean;
  headingLevel?: "h2" | "h3";
  exclude?: string;
};

export function Services({ compact = false, headingLevel = "h3", exclude }: Props) {
  const list = exclude ? services.filter((s) => s.slug !== exclude) : services;
  return (
    <section id="services" className={compact ? "section bg-ivory" : "section bg-ivory"}>
      <div className="container-site">
        {!compact && (
          <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <SectionHeading
              eyebrow="Our repair services"
              title="Window and door repairs for every type of property"
              intro="Fourteen core services covering the mechanical, glazing and frame faults we are asked about most. Each one is a repair first, with replacement recommended only when it is genuinely the better outcome."
            />
            <Button href="/contact" variant="secondary" className="shrink-0">
              Request a quote
            </Button>
          </div>
        )}
        <ul className={`grid gap-6 sm:grid-cols-2 lg:grid-cols-3 ${compact ? "" : "mt-12"}`}>
          {list.map((s) => (
            <li key={s.slug}>
              <ServiceCard service={s} headingLevel={headingLevel} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
