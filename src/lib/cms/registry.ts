import { type FieldSpec, validateCollection, type ValidationResult } from "@/lib/cms/validate";
import { COLLECTION_GUIDES } from "@/lib/cms/guides";

export type CollectionMode = "object" | "list";

export type Collection = {
  id: string; // URL-safe id used in API + edit routes
  label: string; // shown in the dashboard
  description: string;
  file: string; // repo-relative path
  mode: CollectionMode;
  idField?: string; // list entries are addressed by this field (default "slug")
  titleField?: string; // which field to show as an entry's title in lists
  fields: FieldSpec[];
  guide?: FieldSpec["guide"]; // picture + directions shown at the top of the section
  /** Page root for a list whose entries are pages (/services, /blog, /case-studies): the slug is editable as the page address and a change is redirected. */
  pathPrefix?: string;
  /** Extra whole-collection checks beyond the field specs. */
  check?: (data: unknown) => string[];
  validate: (data: unknown) => ValidationResult;
};

const ctaFields: FieldSpec[] = [
  { key: "label", label: "Button text", type: "string", required: true, max: 60 },
  { key: "href", label: "Button link (a page like /contact, a section like #quote-form, or https://…)", type: "string", format: "path", required: true },
];

const linkFields: FieldSpec[] = [
  { key: "label", type: "string", required: true, max: 80 },
  { key: "href", label: "Link (e.g. /services/sash-window-repairs)", type: "string", format: "path", required: true },
];

const headingFields: FieldSpec[] = [
  { key: "eyebrow", label: "Small label", type: "string", required: true, max: 60 },
  { key: "title", type: "string", required: true },
  { key: "description", label: "Intro line", type: "text", required: true, max: 400 },
];

const bannerFields: FieldSpec[] = [
  { key: "eyebrow", label: "Small label", type: "string", required: true, max: 60 },
  { key: "title", label: "Banner title", type: "string", required: true },
  { key: "description", label: "Banner intro line", type: "text", required: true, max: 400 },
];

const bannerWithCtaFields: FieldSpec[] = [
  ...bannerFields,
  { key: "ctaTitle", label: "Closing banner title", type: "string", required: true, max: 120 },
  { key: "ctaDescription", label: "Closing banner text", type: "text", required: true, max: 300 },
];

const seoOverrideFields: FieldSpec[] = [
  { key: "seoTitle", label: "SEO title (optional: empty uses the article title)", type: "string", max: 90 },
  { key: "seoDescription", label: "Meta description (optional: empty uses the summary)", type: "text", max: 220 },
];

const CASE_STUDY_CATEGORIES = ["Sash windows", "uPVC", "Aluminium", "Double glazing", "Doors", "Commercial"] as const;

const seoFields: FieldSpec[] = [
  { key: "title", label: "SEO title (aim for 50-60 characters)", type: "string", required: true, max: 90 },
  { key: "description", label: "Meta description (aim for 140-160 characters)", type: "text", required: true, max: 220 },
];

const photoFields: FieldSpec[] = [
  { key: "src", label: "Picture", type: "string", format: "image", required: true },
  { key: "alt", label: "Picture description (alt text)", type: "string", required: true, max: 200 },
];

const legalDocFields: FieldSpec[] = [
  { key: "updated", label: "Last updated (e.g. November 2026)", type: "string", required: true, max: 40 },
  {
    key: "sections",
    label: "Sections",
    type: "object[]",
    required: true,
    itemLabel: "Section",
    fields: [
      { key: "title", label: "Section title", type: "string", required: true },
      { key: "body", label: 'Paragraphs (start a line with "- " for a bullet point)', type: "string[]", required: true, max: 1500 },
    ],
  },
];

const pointFields: FieldSpec[] = [
  { key: "slug", type: "string", format: "slug", required: true },
  { key: "title", type: "string", required: true, max: 80 },
  { key: "text", type: "text", required: true, max: 400 },
];

const TRUST_ICONS = ["building", "wrench", "file", "map"] as const;
const WHY_ICONS = ["search", "building", "hammer", "file", "map", "message"] as const;

/** Extra checks for the Redirects list: no rule may point at itself or at a section anchor. */
function checkRedirects(data: unknown): string[] {
  if (!Array.isArray(data)) return [];
  const errors: string[] = [];
  data.forEach((r) => {
    const rec = r as { from?: unknown; to?: unknown };
    if (typeof rec.from !== "string" || typeof rec.to !== "string") return;
    if (rec.to.startsWith("#")) errors.push(`${rec.from}: the new address cannot be a section (#); use a page like /contact`);
    if (rec.from === rec.to.replace(/\/$/, "")) errors.push(`${rec.from}: the old and new address are the same`);
  });
  return errors;
}

const defs: Omit<Collection, "validate">[] = [
  /* ---------------------------------------------------------------- Site ---- */
  {
    id: "settings",
    label: "Site settings",
    description: "Company name, tagline, description, the live site address, profile links, and the analytics and verification codes.",
    file: "src/content/settings.json",
    mode: "object",
    check: (data) => {
      const links = (data as { sameAs?: unknown }).sameAs;
      return Array.isArray(links) ? links.filter((l) => typeof l === "string" && l.trim() && !/^https:\/\/\S+$/.test(l.trim())).map((l) => `Profile link "${l}" must be a full https:// address`) : [];
    },
    fields: [
      { key: "name", label: "Company name", type: "string", required: true, max: 80 },
      { key: "shortName", label: "Short name", type: "string", required: true, max: 40 },
      { key: "legalLine", label: "Copyright line (footer)", type: "string", required: true, max: 120 },
      { key: "tagline", type: "string", required: true, max: 160 },
      { key: "description", label: "Site description (default for search engines and social previews)", type: "text", required: true, max: 400 },
      { key: "url", label: "Live site address", type: "string", format: "url", required: true },
      { key: "region", label: "Service area name (e.g. Greater London and the Thames Valley)", type: "string", required: true, max: 60, help: "Used in the structured data and in the service page meta descriptions." },
      {
        key: "ga4MeasurementId",
        label: "Google Analytics 4 Measurement ID (e.g. G-XXXXXXXXXX)",
        type: "string",
        max: 20,
        help: "Empty = no analytics. Set it and publish: GA4 then records page views, phone, WhatsApp and email clicks, and quote form submits (generate_lead).",
      },
      {
        key: "googleSiteVerification",
        label: "Google Search Console verification code (the content value of the HTML tag)",
        type: "string",
        max: 120,
        help: "Paste only the code, not the whole <meta> tag. Empty = no tag.",
      },
      {
        key: "sameAs",
        label: "Profile links (Google Business Profile, Facebook, Instagram, …), one full https:// address per line",
        type: "string[]",
        max: 200,
        help: "Published in the business structured data as sameAs. Empty = none.",
      },
      {
        key: "bingSiteVerification",
        label: "Bing Webmaster verification code (the content value of the msvalidate.01 tag)",
        type: "string",
        max: 120,
        help: "Paste only the code, not the whole <meta> tag. Empty = no tag.",
      },
    ],
  },
  {
    id: "home",
    label: "Home page",
    description: "The hero (headline, buttons, reassurance lines) and the introduction block.",
    file: "src/content/home.json",
    mode: "object",
    fields: [
      {
        key: "hero",
        label: "Hero",
        type: "object",
        required: true,
        fields: [
          { key: "eyebrow", label: "Small label", type: "string", required: true, max: 60 },
          { key: "title", label: "Headline", type: "string", required: true, max: 120 },
          { key: "subtitle", label: "Text under the headline", type: "text", required: true, max: 400 },
          { key: "primaryCta", label: "Primary button", type: "object", required: true, fields: ctaFields },
          { key: "secondaryCta", label: "Secondary button", type: "object", required: true, fields: ctaFields },
          { key: "reassurance", label: "Ticked lines under the buttons", type: "string[]", required: true, max: 120 },
          { key: "imageCaption", label: "Caption under the photo (optional)", type: "string", max: 200 },
        ],
      },
      {
        key: "intro",
        label: "Introduction block",
        type: "object",
        required: true,
        fields: [
          { key: "eyebrow", label: "Small label", type: "string", required: true, max: 60 },
          { key: "title", type: "string", required: true, max: 120 },
          { key: "paragraphs", label: "Paragraphs (one item per paragraph)", type: "string[]", required: true, max: 1500 },
          { key: "quickLinks", label: "Quick links", type: "object[]", itemLabel: "Link", fields: linkFields },
          { key: "cta", label: "Button", type: "object", required: true, fields: ctaFields },
        ],
      },
    ],
  },
  {
    id: "sections",
    label: "Section headings",
    description: "The small label, title and intro line above each block of the site, plus button labels.",
    file: "src/content/sections.json",
    mode: "object",
    fields: [
      { key: "services", label: "Services grid (home)", type: "object", required: true, fields: [...headingFields, { key: "buttonLabel", type: "string", required: true, max: 60 }] },
      { key: "whyUs", label: "Why choose us", type: "object", required: true, fields: [...headingFields, { key: "buttonLabel", type: "string", required: true, max: 60 }] },
      { key: "process", label: "How it works", type: "object", required: true, fields: headingFields },
      {
        key: "areas",
        label: "Areas we cover (home)",
        type: "object",
        required: true,
        fields: [...headingFields, { key: "note", label: "Note in the box under the areas", type: "text", required: true, max: 400 }, { key: "buttonLabel", type: "string", required: true, max: 60 }],
      },
      {
        key: "testimonials",
        label: "Customer feedback",
        type: "object",
        required: true,
        fields: [...headingFields, { key: "placeholderNotice", label: "Notice shown while any testimonial is sample content", type: "string", required: true, max: 200 }],
      },
      {
        key: "pricing",
        label: "Quotations band",
        type: "object",
        required: true,
        fields: [
          ...headingFields,
          { key: "factorsHeading", label: "Heading over the list", type: "string", required: true, max: 80 },
          { key: "primaryLabel", label: "Primary button text", type: "string", required: true, max: 60 },
          { key: "secondaryLabel", label: "Secondary button text (opens the FAQs)", type: "string", required: true, max: 60 },
        ],
      },
      { key: "faq", label: "FAQ", type: "object", required: true, fields: [...headingFields, { key: "buttonLabel", type: "string", required: true, max: 60 }] },
      {
        key: "quote",
        label: "Enquiry form section",
        type: "object",
        required: true,
        fields: [
          ...headingFields,
          { key: "stepsHeading", label: "Heading over the steps", type: "string", required: true, max: 80 },
          { key: "note", label: "Closing note under the steps", type: "text", required: true, max: 400 },
          { key: "submitLabel", label: "Send button text", type: "string", required: true, max: 60 },
          { key: "privacyLine", label: "Line beside the send button", type: "string", required: true, max: 160 },
        ],
      },
      {
        key: "cta",
        label: "Teal call-to-action band (inner pages)",
        type: "object",
        required: true,
        fields: [
          { key: "title", type: "string", required: true, max: 120 },
          { key: "description", type: "text", required: true, max: 300 },
          { key: "buttonLabel", type: "string", required: true, max: 60 },
        ],
      },
      {
        key: "caseStudies",
        label: "Case studies (home)",
        type: "object",
        required: true,
        fields: [
          ...headingFields,
          { key: "buttonLabel", type: "string", required: true, max: 60 },
          { key: "placeholderNotice", label: "Notice shown while any case study is sample content", type: "string", required: true, max: 200 },
        ],
      },
      { key: "blog", label: "Blog teasers (home)", type: "object", required: true, fields: [...headingFields, { key: "buttonLabel", type: "string", required: true, max: 60 }] },
    ],
  },
  {
    id: "pages",
    label: "Page banners & copy",
    description: "The banner at the top of each inner page, and the body text of the About and Areas pages.",
    file: "src/content/pages.json",
    mode: "object",
    fields: [
      {
        key: "services",
        label: "Services page",
        type: "object",
        required: true,
        fields: [
          ...bannerFields,
          { key: "coverageLine", label: "Line above the area links on every service page (Where we carry out this work)", type: "text", required: true, max: 200 },
        ],
      },
      {
        key: "about",
        label: "About page",
        type: "object",
        required: true,
        fields: [
          ...bannerFields,
          { key: "bodyTitle", label: "Heading of the text block", type: "string", required: true, max: 140 },
          { key: "paragraphs", label: "Paragraphs", type: "string[]", required: true, max: 1500 },
          { key: "captionOne", label: "Caption under the first small photo", type: "string", max: 120 },
          { key: "captionTwo", label: "Caption under the second small photo", type: "string", max: 120 },
          {
            key: "facts",
            label: "The three facts (who we help, what we repair, where we work)",
            type: "object[]",
            itemLabel: "Fact",
            fields: [
              { key: "title", type: "string", required: true, max: 60 },
              { key: "text", type: "text", required: true, max: 300 },
            ],
          },
        ],
      },
      {
        key: "areas",
        label: "Areas page",
        type: "object",
        required: true,
        fields: [
          ...bannerFields,
          { key: "bodyTitle", label: "Heading of the text block", type: "string", required: true, max: 140 },
          { key: "paragraphs", label: "Paragraphs", type: "string[]", required: true, max: 1500 },
        ],
      },
      {
        key: "faqs",
        label: "FAQs page",
        type: "object",
        required: true,
        fields: [
          ...bannerFields,
          { key: "ctaTitle", label: "Closing banner title", type: "string", required: true, max: 120 },
          { key: "ctaDescription", label: "Closing banner text", type: "text", required: true, max: 300 },
        ],
      },
      { key: "caseStudies", label: "Case Studies page", type: "object", required: true, fields: bannerWithCtaFields },
      { key: "blog", label: "Blog page", type: "object", required: true, fields: bannerWithCtaFields },
      { key: "contact", label: "Contact page", type: "object", required: true, fields: bannerFields },
      { key: "privacy", label: "Privacy Policy page", type: "object", required: true, fields: bannerFields },
      { key: "terms", label: "Terms & Conditions page", type: "object", required: true, fields: bannerFields },
    ],
  },
  {
    id: "images",
    label: "Photographs",
    description: "The pictures on the home, About and Areas pages. Service photos are inside each Services entry.",
    file: "src/content/images.json",
    mode: "object",
    fields: [
      { key: "hero", label: "Home: hero photo", type: "object", required: true, fields: photoFields },
      { key: "intro", label: "Home: introduction photo", type: "object", required: true, fields: photoFields },
      { key: "about", label: "About: main photo", type: "object", required: true, fields: photoFields },
      { key: "workshop", label: "About: first small photo", type: "object", required: true, fields: photoFields },
      { key: "commercialExterior", label: "About: second small photo", type: "object", required: true, fields: photoFields },
      { key: "areas", label: "Areas page photo", type: "object", required: true, fields: photoFields },
    ],
  },
  {
    id: "contact",
    label: "Contact details",
    description: "Phone, WhatsApp, email, address, opening hours and the map on the Contact page, plus the floating WhatsApp button. Leave anything empty to hide it.",
    file: "src/content/contact.json",
    mode: "object",
    fields: [
      { key: "detailsTitle", label: "Heading", type: "string", required: true, max: 80 },
      { key: "detailsIntro", label: "Intro line", type: "text", max: 300 },
      { key: "whatsappNumber", label: "WhatsApp number with country code, digits only (e.g. 447700900123)", type: "string", max: 20, help: "Empty = no WhatsApp buttons anywhere on the site." },
      { key: "whatsappLabel", label: "WhatsApp button text", type: "string", max: 40 },
      { key: "whatsappMessage", label: "Message typed in for the customer when they open WhatsApp", type: "text", max: 200 },
      { key: "phone", label: "Phone number as shown (e.g. +44 20 1234 5678)", type: "string", max: 30 },
      { key: "email", label: "Email address", type: "string", format: "email", max: 120 },
      { key: "addressTitle", label: "Address heading (e.g. Office)", type: "string", max: 40 },
      { key: "address", label: "Address lines", type: "string[]", max: 80 },
      { key: "hoursTitle", label: "Opening hours heading", type: "string", max: 40 },
      { key: "hours", label: "Opening hours lines", type: "string[]", max: 80 },
      {
        key: "openingHoursSchema",
        label: "Opening hours for Google (structured data), one rule per line",
        type: "string[]",
        max: 40,
        help: "Google's format: Mo-Fr 08:00-18:00, Sa 09:00-13:00. Days Mo Tu We Th Fr Sa Su, 24-hour times. Keep it in step with the lines above. Empty = not published.",
      },
      { key: "mapTitle", label: "Caption under the map", type: "string", max: 80 },
      { key: "mapQuery", label: "Map: the address or place to show (e.g. 12 High Street, Croydon CR0 1AA)", type: "string", max: 160, help: "Empty = no map." },
      {
        key: "mapEmbedUrl",
        label: "Map: Google Maps embed address (optional, overrides the line above)",
        type: "string",
        max: 400,
        help: "In Google Maps: Share > Embed a map > copy only the https://www.google.com/maps/embed?… address from the code.",
      },
      { key: "showFloatingButton", label: "Show the floating WhatsApp button on every page", type: "boolean" },
      { key: "floatingLabel", label: "Floating button text", type: "string", max: 30 },
    ],
  },
  {
    id: "form",
    label: "Enquiry form",
    description: "The dropdown choices and the wording on the enquiry form.",
    file: "src/content/form.json",
    mode: "object",
    fields: [
      { key: "propertyTypeOptions", label: "Property type choices", type: "string[]", required: true, max: 60 },
      { key: "serviceOptions", label: "Service required choices", type: "string[]", required: true, max: 60 },
      { key: "contactTimeOptions", label: "Preferred contact time choices", type: "string[]", required: true, max: 40 },
      { key: "postcodeHint", label: "Line under the Postcode box", type: "text", max: 160, help: "Empty = no line." },
      {
        key: "outsideAreaNotice",
        label: "Notice shown when the postcode is outside the London postcode areas",
        type: "text",
        max: 300,
        help: "Empty (the default) = the postcode is never checked against London. Only fill this in if the business goes back to London only.",
      },
    ],
  },
  {
    id: "seo",
    label: "SEO titles & descriptions",
    description: 'Search-engine title and meta description for each page. " | Best View Glazing Ltd" is added after every title automatically, except the home page.',
    file: "src/content/seo.json",
    mode: "object",
    fields: [
      { key: "home", label: "Home page (full title, no suffix added)", type: "object", required: true, fields: seoFields },
      { key: "services", label: "Services page", type: "object", required: true, fields: seoFields },
      { key: "about", label: "About page", type: "object", required: true, fields: seoFields },
      { key: "areas", label: "Areas page", type: "object", required: true, fields: seoFields },
      { key: "faqs", label: "FAQs page", type: "object", required: true, fields: seoFields },
      { key: "contact", label: "Contact page", type: "object", required: true, fields: seoFields },
      { key: "privacy", label: "Privacy Policy page", type: "object", required: true, fields: seoFields },
      { key: "terms", label: "Terms & Conditions page", type: "object", required: true, fields: seoFields },
      { key: "caseStudies", label: "Case Studies page", type: "object", required: true, fields: seoFields },
      { key: "blog", label: "Blog page (articles have their own SEO fields)", type: "object", required: true, fields: seoFields },
      { key: "keywords", label: "Site keywords", type: "string[]", max: 60 },
    ],
  },
  {
    id: "footer",
    label: "Footer",
    description: "The paragraph under the logo, the column headings and the bottom line.",
    file: "src/content/footer.json",
    mode: "object",
    fields: [
      { key: "intro", label: "Paragraph under the logo", type: "text", required: true, max: 400 },
      { key: "quoteLinkLabel", label: "Quote link text", type: "string", required: true, max: 60 },
      { key: "navigationHeading", type: "string", required: true, max: 40 },
      { key: "servicesHeading", type: "string", required: true, max: 40 },
      { key: "areasHeading", type: "string", required: true, max: 40 },
      { key: "legalHeading", type: "string", required: true, max: 40 },
      { key: "bottomLine", label: "Text beside the copyright line", type: "string", required: true, max: 200 },
    ],
  },
  {
    id: "legal",
    label: "Legal pages",
    description: "The full text of the Privacy Policy and Terms & Conditions pages.",
    file: "src/content/legal.json",
    mode: "object",
    fields: [
      { key: "privacy", label: "Privacy Policy", type: "object", required: true, fields: legalDocFields },
      { key: "terms", label: "Terms & Conditions", type: "object", required: true, fields: legalDocFields },
    ],
  },

  /* --------------------------------------------------------- Collections ---- */
  {
    id: "services",
    label: "Services",
    description: "The fourteen repair services: the cards on the home page and each service's own page.",
    file: "src/content/services.json",
    mode: "list",
    titleField: "title",
    pathPrefix: "/services",
    fields: [
      { key: "slug", type: "string", format: "slug", required: true },
      { key: "title", type: "string", required: true, max: 80 },
      { key: "summary", label: "Summary (card and page banner)", type: "text", required: true, max: 220 },
      { key: "image", label: "Photo", type: "string", format: "image", required: true },
      { key: "imageAlt", label: "Photo description (alt text)", type: "string", required: true, max: 200 },
      { key: "body", label: "Service page paragraphs (one item per paragraph)", type: "string[]", required: true, max: 1500 },
      { key: "faults", label: "Common faults we repair (one per line)", type: "string[]", max: 120 },
      { key: "formLabel", label: "Form label (must match a Service required choice in Enquiry form)", type: "string", required: true, max: 60 },
      { key: "seoTitle", label: "SEO title for the service page", type: "string", required: true, max: 90 },
      {
        key: "faqs",
        label: "Questions and answers for this service (shown on the page, with FAQ schema)",
        type: "object[]",
        itemLabel: "Question",
        fields: [
          { key: "question", type: "string", required: true, max: 180 },
          { key: "answer", type: "text", required: true, max: 1500 },
        ],
      },
      { key: "icon", label: "Icon name (leave as it is)", type: "string", max: 40 },
    ],
  },
  {
    id: "regions",
    label: "Areas we cover",
    description: "The regions (columns on the Areas page). Regions outside London are fine, e.g. Berkshire & Buckinghamshire. The towns and districts inside each region are edited under Area pages.",
    file: "src/content/regions.json",
    mode: "list",
    titleField: "region",
    fields: [
      { key: "slug", type: "string", format: "slug", required: true },
      { key: "region", label: "Region name", type: "string", required: true, max: 60 },
      { key: "intro", label: "Intro line (Areas page)", type: "text", required: true, max: 400 },
    ],
  },
  {
    id: "area-pages",
    label: "Area pages",
    description: "One entry per town or district. It is listed under its region on the Areas page; its own page at /areas/<address> exists only while Publish page is on, and should have its own content first.",
    file: "src/content/area-pages.json",
    mode: "list",
    titleField: "name",
    pathPrefix: "/areas",
    fields: [
      { key: "slug", type: "string", format: "slug", required: true },
      { key: "name", label: "Town or district name", type: "string", required: true, max: 60 },
      { key: "regionSlug", label: "Region (from Areas we cover)", type: "string", required: true, enumFrom: { collection: "regions", valueField: "slug" } },
      {
        key: "published",
        label: "Publish page",
        type: "boolean",
        help: "Off (default): a plain name on the Areas page, no page, not in the sitemap, /areas/<address> redirects to /areas. On: the page is live and linked. Switch on only once the content below is written.",
      },
      { key: "h1", label: "H1 (page heading; empty = Window & Door Repairs in <name>)", type: "string", max: 120 },
      { key: "intro", label: "Banner intro (empty = a standard sentence)", type: "text", max: 600 },
      { key: "image", label: "Photo (top of the page, optional)", type: "string", format: "image" },
      { key: "imageAlt", label: "Photo description (alt text)", type: "string", max: 200 },
      {
        key: "sections",
        label: "Content sections, each with its own H2",
        type: "object[]",
        itemLabel: "Section",
        fields: [
          { key: "heading", label: "Heading (H2)", type: "string", required: true, max: 140 },
          { key: "paragraphs", label: "Paragraphs (one block per paragraph)", type: "string[]", required: true, max: 1500, longText: true },
          { key: "image", label: "Photo (optional)", type: "string", format: "image" },
          { key: "imageAlt", label: "Photo description (alt text)", type: "string", max: 200 },
          { key: "imageSide", label: "Photo side at desktop width", type: "string", enum: ["right", "left"] },
        ],
      },
      { key: "nearby", label: "Nearby places (one per line; a name that matches a published area page becomes a link)", type: "string[]", max: 60 },
      {
        key: "faqs",
        label: "Questions and answers for this area (shown on the page, with FAQ schema)",
        type: "object[]",
        itemLabel: "Question",
        fields: [
          { key: "question", type: "string", required: true, max: 180 },
          { key: "answer", type: "text", required: true, max: 1500 },
        ],
      },
      { key: "seoTitle", label: "SEO title (empty = Window & Door Repairs <name>)", type: "string", max: 90 },
      { key: "seoDescription", label: "Meta description (empty = a standard sentence)", type: "text", max: 220 },
    ],
  },
  {
    id: "redirects",
    label: "Redirects",
    description: "Old addresses that send visitors (and search engines) to a new page, each in one hop. Filled in automatically when a page address changes; add your own for pages you remove.",
    file: "src/content/redirects.json",
    mode: "list",
    idField: "from",
    titleField: "from",
    check: checkRedirects,
    fields: [
      { key: "from", label: "Old address (e.g. /services/old-name)", type: "string", format: "sitePath", required: true, max: 200 },
      {
        key: "to",
        label: "New address (a page like /services/new-name, or https://...)",
        type: "string",
        format: "path",
        required: true,
        max: 200,
        help: "Visitors get a permanent (301/308) redirect. If the new address is itself redirected later, the rules are joined so it stays one hop.",
      },
      { key: "note", label: "Note (optional)", type: "string", max: 120 },
    ],
  },
  {
    id: "posts",
    label: "Blog articles",
    description: "Advice articles. The first three show on the home page, so keep the newest at the top.",
    file: "src/content/posts.json",
    mode: "list",
    titleField: "title",
    pathPrefix: "/blog",
    fields: [
      { key: "slug", type: "string", format: "slug", required: true },
      { key: "title", type: "string", required: true, max: 120 },
      { key: "category", label: "Category (e.g. Double glazing, Sash windows, Landlords)", type: "string", required: true, max: 40 },
      { key: "date", label: "Date (e.g. 12 November 2026)", type: "string", max: 40 },
      { key: "readingTime", label: "Reading time (e.g. 5 min read)", type: "string", max: 24 },
      { key: "excerpt", label: "Summary (card and banner)", type: "text", required: true, max: 280 },
      { key: "image", label: "Picture", type: "string", format: "image", required: true },
      { key: "imageAlt", label: "Picture description (alt text)", type: "string", required: true, max: 200 },
      { key: "body", label: "Article", type: "string[]", longText: true, required: true, max: 1500 },
      ...seoOverrideFields,
    ],
  },
  {
    id: "case-studies",
    label: "Case studies",
    description: "Examples of past work. The first three show on the home page. Tick Sample content on any entry that is not a real project yet.",
    file: "src/content/case-studies.json",
    mode: "list",
    titleField: "title",
    pathPrefix: "/case-studies",
    fields: [
      { key: "slug", type: "string", format: "slug", required: true },
      { key: "title", type: "string", required: true, max: 120 },
      { key: "category", type: "string", enum: CASE_STUDY_CATEGORIES, required: true },
      { key: "location", label: "Location (e.g. Islington, North London)", type: "string", required: true, max: 80 },
      { key: "excerpt", label: "One-line summary (card)", type: "text", required: true, max: 280 },
      { key: "description", label: "Description (top of the case-study page)", type: "text", required: true, max: 1200 },
      { key: "image", label: "Picture", type: "string", format: "image", required: true },
      { key: "imageAlt", label: "Picture description (alt text)", type: "string", required: true, max: 200 },
      { key: "tags", label: "Work carried out (short tags)", type: "string[]", max: 40 },
      {
        key: "results",
        label: "Results (up to three numbers)",
        type: "object[]",
        itemLabel: "Result",
        fields: [
          { key: "label", type: "string", required: true, max: 40 },
          { key: "value", type: "string", required: true, max: 24 },
        ],
      },
      { key: "body", label: "Full write-up (optional)", type: "string[]", longText: true, max: 1500 },
      { key: "placeholder", label: "Sample content (not a real project yet)", type: "boolean" },
    ],
  },
  {
    id: "faqs",
    label: "FAQs",
    description: "Questions and answers.",
    file: "src/content/faqs.json",
    mode: "list",
    titleField: "question",
    fields: [
      { key: "slug", type: "string", format: "slug", required: true },
      { key: "question", type: "string", required: true },
      { key: "answer", type: "text", required: true },
    ],
  },
  {
    id: "testimonials",
    label: "Testimonials",
    description: "Customer feedback cards. Tick Sample content on any placeholder quote.",
    file: "src/content/testimonials.json",
    mode: "list",
    titleField: "name",
    fields: [
      { key: "slug", type: "string", format: "slug", required: true },
      { key: "name", label: "Customer name", type: "string", required: true, max: 80 },
      { key: "location", label: "General location (e.g. Islington, North London)", type: "string", required: true, max: 80 },
      { key: "quote", type: "text", required: true, max: 600 },
      { key: "rating", label: "Stars out of 5 (0 = none)", type: "number", min: 0, max: 5 },
      { key: "placeholder", label: "Sample content (not a real customer yet)", type: "boolean" },
    ],
  },
  {
    id: "trust-points",
    label: "Trust strip",
    description: "The four points in the dark band under the hero.",
    file: "src/content/trust-points.json",
    mode: "list",
    titleField: "title",
    fields: [...pointFields, { key: "icon", type: "string", enum: TRUST_ICONS, required: true }],
  },
  {
    id: "why-us",
    label: "Why choose us",
    description: "The six points on the home and About pages.",
    file: "src/content/why-us.json",
    mode: "list",
    titleField: "title",
    fields: [...pointFields, { key: "icon", type: "string", enum: WHY_ICONS, required: true }],
  },
  {
    id: "process",
    label: "How it works",
    description: "The numbered steps, in order.",
    file: "src/content/process.json",
    mode: "list",
    titleField: "title",
    fields: pointFields,
  },
  {
    id: "quote-factors",
    label: "Quotation factors",
    description: "What affects the cost of a repair, in order.",
    file: "src/content/quote-factors.json",
    mode: "list",
    titleField: "title",
    fields: pointFields,
  },
];

export const collections: Collection[] = defs.map((d) => ({
  ...d,
  guide: COLLECTION_GUIDES[d.id],
  idField: d.mode === "list" ? (d.idField ?? "slug") : undefined,
  validate: (data: unknown) => {
    const base = validateCollection({ mode: d.mode, idField: d.idField ?? "slug", fields: d.fields }, data);
    const extra = d.check ? d.check(data) : [];
    if (extra.length === 0) return base;
    return { ok: false, errors: [...(base.ok ? [] : base.errors), ...extra] };
  },
}));

const byId = Object.fromEntries(collections.map((c) => [c.id, c]));
export const getCollection = (id: string): Collection | undefined => byId[id];

/** Map a repo file path back to its collection (for labelling diffs). */
export const collectionByFile = (file: string) => collections.find((c) => c.file === file || file.endsWith(c.file));
