import { Building2, Clock, FileText, MapPin, ShieldCheck, Wrench, type LucideIcon } from "lucide-react";
import { trustPoints } from "@/content/site";

const icons: Record<string, LucideIcon> = { building: Building2, wrench: Wrench, file: FileText, map: MapPin, clock: Clock, shield: ShieldCheck };

export function TrustStrip() {
  return (
    <section aria-label="Why customers choose us" className="bg-charcoal text-white">
      <div className="container-site">
        <ul className="grid grid-cols-1 divide-y divide-line-dark sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4">
          {trustPoints.map((point, i) => {
            const Icon = icons[point.icon] ?? Wrench;
            return (
              <li
                key={point.slug}
                className={`flex gap-4 py-6 sm:px-6 lg:py-8 ${i % 2 === 1 ? "sm:border-l sm:border-line-dark" : ""} ${
                  i >= 2 ? "sm:border-t sm:border-line-dark lg:border-t-0" : ""
                } ${i > 0 ? "lg:border-l lg:border-line-dark" : ""} first:sm:pl-0 last:lg:pr-0`}
              >
                <Icon className="mt-0.5 h-6 w-6 shrink-0 text-brass" strokeWidth={1.75} aria-hidden="true" />
                <div>
                  <h3 className="font-heading text-base font-semibold text-white">{point.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-white/70">{point.text}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
