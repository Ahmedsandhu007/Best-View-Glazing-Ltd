import Image from "next/image";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { images } from "@/content/images";
import { site } from "@/content/site";

const reassurance = [
  "Residential and commercial properties",
  "Written quotation before any work is agreed",
  "Repair first, replacement only when it is the right answer",
];

export function Hero() {
  const img = images.hero;
  return (
    <section className="border-b border-line bg-ivory">
      <div className="container-site grid items-center gap-10 py-14 md:py-20 lg:grid-cols-12 lg:gap-14 lg:py-24">
        <div className="lg:col-span-6">
          <p className="eyebrow">Greater London · Windows &amp; Doors</p>
          <h1 className="mt-4 text-[2.5rem] font-bold leading-[1.08] md:text-5xl lg:text-[3.375rem]">
            Professional Window &amp; Door Repairs Across London
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
            Reliable repair solutions for residential and commercial properties. From faulty window mechanisms and
            damaged locks to glazing problems and worn-out frames, our services are focused on restoring security,
            functionality and peace of mind.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button href={`#${site.enquiryFormId}`} size="lg">
              Request a Free Quote
            </Button>
            <Button href="/services" variant="secondary" size="lg">
              View Our Services
            </Button>
          </div>
          <ul className="mt-9 space-y-2 border-t border-line pt-6 text-[0.9375rem] text-ink">
            {reassurance.map((item) => (
              <li key={item} className="flex items-start gap-2.5">
                <Check className="mt-1 h-4 w-4 shrink-0 text-teal" aria-hidden="true" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="lg:col-span-6">
          <figure className="relative">
            <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory-deep sm:aspect-[5/4] lg:aspect-[5/5.4]">
              <Image
                src={img.src}
                alt={img.alt}
                fill
                priority
                fetchPriority="high"
                sizes="(min-width: 1024px) 560px, 100vw"
                className="object-cover"
              />
            </div>
            <figcaption className="mt-3 text-sm text-muted">
              Timber sash, uPVC, aluminium and composite units repaired across the capital.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
