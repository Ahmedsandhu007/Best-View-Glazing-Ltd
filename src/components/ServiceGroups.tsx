import { AppWindow, Building2, Lock, Sparkles, type LucideIcon } from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";
import { RichInline } from "@/components/RichText";
import { home, sections } from "@/content/site";

const icons: Record<string, LucideIcon> = { window: AppWindow, glass: Sparkles, lock: Lock, building: Building2 };

/** Home page: the four service groups, each a short paragraph whose links go to the service pages. */
export function ServiceGroups() {
  const copy = sections.services;
  const groups = home.serviceGroups;
  if (groups.length === 0) return null;
  return (
    <section id="services" className="section bg-ivory">
      <div className="container-site">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={<RichInline text={copy.description} />} />
          <Button href="/services" variant="secondary" className="shrink-0">
            {copy.buttonLabel}
          </Button>
        </div>
        <ul className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {groups.map((g) => {
            const Icon = icons[g.icon] ?? AppWindow;
            return (
              <li key={g.heading} className="flex flex-col rounded-[4px] border border-line bg-white p-6">
                <span className="flex h-11 w-11 items-center justify-center rounded-[4px] bg-teal-tint text-teal">
                  <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
                </span>
                <h3 className="mt-4 font-heading text-[1.125rem] font-semibold leading-snug text-charcoal">{g.heading}</h3>
                <p className="mt-2.5 text-[0.9375rem] leading-relaxed text-ink">
                  <RichInline text={g.text} />
                </p>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
