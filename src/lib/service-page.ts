/**
 * Resolves what a service page shows: the site-wide defaults from
 * src/content/service-page.json ("Service page blocks" in the CMS) overridden
 * per service by its `blocks` field. "{service}" in a heading or intro becomes
 * the service title in lower case.
 */
import servicePageData from "@/content/service-page.json";
import { processSteps, quoteFactors, whyChooseUs } from "@/content/site";
import type { Service, ServiceBlockMode, TitledPoint } from "@/content/services";

export type ServicePageDefaults = {
  heroForm: { enabled: boolean; title: string; intro: string; buttonLabel: string; note: string };
  stickyBar: { enabled: boolean; callLabel: string; whatsappLabel: string };
  whyUs: { enabled: boolean; heading: string };
  benefits: { enabled: boolean; heading: string; items: string[] };
  process: { enabled: boolean; heading: string };
  cost: { enabled: boolean; heading: string; intro: string };
  faqs: { heading: string };
  coverage: { heading: string };
};

export const servicePageDefaults = servicePageData as ServicePageDefaults;

export function fillService(text: string | undefined, service: Service) {
  return (text ?? "").replace(/\{service\}/gi, service.title.toLowerCase());
}

const on = (mode: ServiceBlockMode | undefined, fallback: boolean) => mode === "on" || (mode !== "off" && fallback);
const pick = (override: string | undefined, fallback: string) => (override?.trim() ? override.trim() : fallback);
const points = (override: TitledPoint[] | undefined, fallback: TitledPoint[]) => {
  const own = (override ?? []).filter((p) => p.title?.trim());
  return own.length ? own : fallback;
};

export type ResolvedServicePage = {
  heroForm: { title: string; intro: string; buttonLabel: string; note: string } | null;
  stickyBar: { callLabel: string; whatsappLabel: string } | null;
  whyUs: { heading: string; items: TitledPoint[] } | null;
  benefits: { heading: string; items: string[] } | null;
  process: { heading: string; items: TitledPoint[] } | null;
  cost: { heading: string; intro: string; items: TitledPoint[] } | null;
  faqsHeading: string;
  coverageHeading: string;
};

export function resolveServicePage(service: Service): ResolvedServicePage {
  const d = servicePageDefaults;
  const b = service.blocks ?? {};
  const benefitItems = (b.benefits?.items ?? []).map((s) => s.trim()).filter(Boolean);
  return {
    heroForm: on(b.heroForm, d.heroForm.enabled)
      ? { title: d.heroForm.title, intro: fillService(d.heroForm.intro, service), buttonLabel: d.heroForm.buttonLabel, note: d.heroForm.note }
      : null,
    stickyBar: on(b.stickyBar, d.stickyBar.enabled) ? { callLabel: d.stickyBar.callLabel, whatsappLabel: d.stickyBar.whatsappLabel } : null,
    whyUs: on(b.whyUs?.mode, d.whyUs.enabled)
      ? { heading: fillService(pick(b.whyUs?.heading, d.whyUs.heading), service), items: points(b.whyUs?.items, whyChooseUs) }
      : null,
    benefits: on(b.benefits?.mode, d.benefits.enabled)
      ? { heading: fillService(pick(b.benefits?.heading, d.benefits.heading), service), items: benefitItems.length ? benefitItems : d.benefits.items }
      : null,
    process: on(b.process?.mode, d.process.enabled)
      ? { heading: fillService(pick(b.process?.heading, d.process.heading), service), items: points(b.process?.items, processSteps) }
      : null,
    cost: on(b.cost?.mode, d.cost.enabled)
      ? {
          heading: fillService(pick(b.cost?.heading, d.cost.heading), service),
          intro: fillService(pick(b.cost?.intro, d.cost.intro), service),
          items: points(b.cost?.items, quoteFactors),
        }
      : null,
    faqsHeading: fillService(pick(b.faqsHeading, d.faqs.heading), service),
    coverageHeading: d.coverage.heading,
  };
}
