import { Building2, FileText, Hammer, MapPin, MessageSquare, SearchCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { site, whyChooseUs } from "@/content/site";

const icons = [SearchCheck, Building2, Hammer, FileText, MapPin, MessageSquare];

export function WhyChooseUs({ ctaHref = `#${site.enquiryFormId}` }: { ctaHref?: string }) {
  return (
    <section className="section bg-white">
      <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-4">
          <div className="lg:sticky lg:top-28">
            <SectionHeading
              eyebrow="Why choose us"
              title="A repair service built around the property and the people in it"
              intro="We are a specialist repair business rather than a window sales company, so the advice you receive is about fixing what you have."
            />
            <div className="mt-8">
              <Button href={ctaHref}>Request a Free Quote</Button>
            </div>
          </div>
        </div>
        <ul className="grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:col-span-8">
          {whyChooseUs.map((item, i) => {
            const Icon = icons[i];
            return (
              <li key={item.title} className="flex gap-4">
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
