import { contact, site } from "@/content/site";
import { services, type Service } from "@/content/services";
import { areaGroups, publishedAreas } from "@/content/areas";
import type { Faq } from "@/content/faqs";
import type { Post } from "@/content/posts";

export function absoluteUrl(path = "/") {
  return new URL(path, site.url).toString();
}

/** Area served: the service-area name from Site settings, the regions, and every district page that is published. */
function areaServed() {
  return [
    { "@type": "AdministrativeArea", name: site.region },
    ...areaGroups.map((g) => ({ "@type": "Place", name: g.region })),
    ...publishedAreas.map((a) => ({ "@type": "Place", name: a.name, url: absoluteUrl(`/areas/${a.slug}`) })),
  ];
}

const openingHours = ((contact as { openingHoursSchema?: string[] }).openingHoursSchema ?? []).map((s) => s.trim()).filter(Boolean);
const sameAs = ((site as { sameAs?: string[] }).sameAs ?? []).map((s) => s.trim()).filter(Boolean);

/**
 * Organisation / local business entity.
 * Address, telephone, opening hours and profile links appear only when entered in the CMS; nothing is invented.
 */
export function organizationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "HomeAndConstructionBusiness",
    "@id": absoluteUrl("/#organisation"),
    name: site.name,
    url: site.url,
    description: site.description,
    image: absoluteUrl("/opengraph-image"),
    logo: absoluteUrl("/icon.svg"),
    // Contact details appear only when the business has entered them in the CMS.
    ...(contact.phone ? { telephone: contact.phone } : {}),
    ...(contact.email ? { email: contact.email } : {}),
    ...(contact.address?.filter(Boolean).length ? { address: { "@type": "PostalAddress", streetAddress: contact.address.filter(Boolean).join(", ") } } : {}),
    ...(openingHours.length ? { openingHours } : {}),
    ...(sameAs.length ? { sameAs } : {}),
    areaServed: areaServed(),
    knowsAbout: services.map((s) => s.title),
    hasOfferCatalog: {
      "@type": "OfferCatalog",
      name: "Window and door repair services",
      itemListElement: services.map((s) => ({
        "@type": "Offer",
        itemOffered: { "@type": "Service", name: s.title, url: absoluteUrl(`/services/${s.slug}`) },
      })),
    },
    potentialAction: {
      "@type": "CommunicateAction",
      name: "Request a quote",
      target: absoluteUrl(site.enquiryPath),
    },
  };
}

export function websiteJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: site.name,
    url: site.url,
    publisher: { "@id": absoluteUrl("/#organisation") },
  };
}

export function serviceJsonLd(service: Service) {
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    name: service.title,
    serviceType: service.title,
    description: service.summary,
    url: absoluteUrl(`/services/${service.slug}`),
    provider: { "@id": absoluteUrl("/#organisation") },
    areaServed: areaServed(),
  };
}

export function faqJsonLd(faqs: Faq[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((f) => ({
      "@type": "Question",
      name: f.question,
      acceptedAnswer: { "@type": "Answer", text: f.answer },
    })),
  };
}

export function blogPostingJsonLd(post: Post) {
  return {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.excerpt,
    image: post.image,
    url: absoluteUrl(`/blog/${post.slug}`),
    ...(post.date ? { datePublished: post.date } : {}),
    author: { "@type": "Organization", name: site.name, "@id": absoluteUrl("/#organisation") },
    publisher: { "@id": absoluteUrl("/#organisation") },
    mainEntityOfPage: absoluteUrl(`/blog/${post.slug}`),
  };
}

export function breadcrumbJsonLd(items: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [{ name: "Home", path: "/" }, ...items].map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: absoluteUrl(item.path),
    })),
  };
}
