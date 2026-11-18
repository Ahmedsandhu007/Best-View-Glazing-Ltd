import { Building2, FileText, Hammer, MapPin, MessageSquare, SearchCheck, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { sections, site, whyChooseUs } from "@/content/site";

const icons: Record<string, LucideIcon> = {
  search: SearchCheck,
  building: Building2,
  hammer: Hammer,
  file: FileText,
  map: MapPin,
  message: MessageSquare,
};
const fallback = [SearchCheck, Building2, Hammer, FileText, MapPin, MessageSquare];

export function WhyChooseUs({ ctaHref = `#${site.enquiryFormId}` }: { ctaHref?: string }) {
  const copy = sections.whyUs;
  return (
    <section className="section bg-white">
      <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-4">
          <div className="lg:sticky lg:top-28">
            <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} />
            <div className="mt-8">
              <Button href={ctaHref}>{copy.buttonLabel}</Button>
            </div>
          </div>
        </div>
        <ul className="grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:col-span-8">
          {whyChooseUs.map((item, i) => {
            const Icon = (item.icon && icons[item.icon]) || fallback[i % fallback.length];
            return (
              <li key={item.slug} className="flex gap-4">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[4px] bg-teal-tint text-teal">
                  <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
                </span>
                <div>
                  <h3 className="font-heading text-[1.0625rem] font-semibold text-charcoal">{item.title}</h3>
                  <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">{item.text}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
