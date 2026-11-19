import { contact, site } from "@/content/site";
import { services, type Service } from "@/content/services";
import { areaGroups } from "@/content/areas";
import type { Faq } from "@/content/faqs";
import type { Post } from "@/content/posts";

export function absoluteUrl(path = "/") {
  return new URL(path, site.url).toString();
}

/**
 * Organisation / local business entity.
 * Deliberately omits address, telephone, opening hours and coordinates:
 * none of those are published for this business and must not be invented.
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
    areaServed: [{ "@type": "AdministrativeArea", name: "Greater London" }, ...areaGroups.map((g) => ({ "@type": "Place", name: g.region }))],
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
    areaServed: { "@type": "AdministrativeArea", name: "Greater London" },
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
