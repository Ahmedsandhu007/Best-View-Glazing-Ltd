import Image from "next/image";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { images } from "@/content/images";
import { home } from "@/content/site";

export function Hero() {
  const img = images.hero;
  const hero = home.hero;
  return (
    <section className="border-b border-line bg-ivory">
      <div className="container-site grid items-center gap-10 py-14 md:py-20 lg:grid-cols-12 lg:gap-14 lg:py-24">
        <div className="lg:col-span-6">
          <p className="eyebrow">{hero.eyebrow}</p>
          <h1 className="mt-4 text-[2.5rem] font-bold leading-[1.08] md:text-5xl lg:text-[3.375rem]">{hero.title}</h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">{hero.subtitle}</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button href={hero.primaryCta.href} size="lg">
              {hero.primaryCta.label}
            </Button>
            <Button href={hero.secondaryCta.href} variant="secondary" size="lg">
              {hero.secondaryCta.label}
            </Button>
          </div>
          <ul className="mt-9 space-y-2 border-t border-line pt-6 text-[0.9375rem] text-ink">
            {hero.reassurance.map((item) => (
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
            {hero.imageCaption ? <figcaption className="mt-3 text-sm text-muted">{hero.imageCaption}</figcaption> : null}
          </figure>
        </div>
      </div>
    </section>
  );
}
