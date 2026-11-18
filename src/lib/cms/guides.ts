import type { FieldSpec } from "@/lib/cms/validate";

type Guide = NonNullable<FieldSpec["guide"]>;

/**
 * "Where does this show up?" panel at the top of each CMS section: a small
 * picture of the page (see components/admin/guide.tsx) plus numbered directions.
 */
export const COLLECTION_GUIDES: Record<string, Guide> = {
  settings: {
    diagram: "settings",
    title: "Site settings: the company details used all over the site",
    steps: [
      "Name: used in page titles, the sign-in page and the copyright line.",
      "Description: the default text search engines and social previews show.",
      "Site address: the live web address; change it only if the domain changes.",
    ],
  },
  home: {
    diagram: "homeHero",
    title: "Home page: the first screen and the introduction block",
    steps: [
      "Small label above the headline.",
      "Headline and the sentence under it.",
      "The two buttons (text and where they go).",
      "The ticked reassurance lines under the buttons.",
      "Introduction: label, title, paragraphs, quick links and button.",
    ],
  },
  sections: {
    diagram: "heading",
    title: "Section headings: the text above each block of the home page",
    steps: [
      "Small label: the short line in capitals.",
      "Title: the large heading.",
      "Intro line: the sentence under the heading.",
      "Each group below is one block of the page (Services, Why choose us, Areas, FAQ, the enquiry form and so on).",
    ],
  },
  pages: {
    diagram: "hero",
    title: "Page banners: the dark banner at the top of each inner page",
    steps: [
      "Banner title, with the small label above it.",
      "Banner intro line.",
      "The About and Areas pages also have their body text here; the FAQs page has its closing banner.",
    ],
  },
  images: {
    diagram: "photos",
    title: "Photographs: the pictures on the home, About and Areas pages",
    steps: [
      "Hero: the large photo beside the headline. Intro: the photo beside the introduction.",
      "About: the main About photo and its two smaller ones. Areas: the photo on the Areas page.",
      "Upload a picture or paste an https image address. The description is read by screen readers and search engines.",
    ],
  },
  form: {
    diagram: "form",
    title: "Enquiry form: the dropdown choices",
    steps: [
      "Property type: the first dropdown.",
      "Service required: the second dropdown. Keep each service's Form label in Services matching one of these.",
      "Preferred contact time: the third dropdown.",
    ],
  },
  seo: {
    diagram: "seo",
    title: "SEO: how each page looks in Google",
    steps: [
      "SEO title: the blue link. \" | Best View Glazing Ltd\" is added automatically, except on the home page.",
      "Meta description: the grey text under it. It is also the text shown when the page is shared.",
      "Service pages use the SEO title inside each Services entry.",
    ],
  },
  footer: {
    diagram: "footer",
    title: "Footer: the bottom of every page",
    steps: [
      "Intro: the short paragraph under the logo, and the quote link beneath it.",
      "Column headings for the navigation, services, areas and legal links.",
      "Bottom line: the text beside the copyright.",
    ],
  },
  legal: {
    diagram: "legal",
    title: "Legal pages: Privacy Policy and Terms & Conditions",
    steps: [
      "Last updated date, shown under the banner.",
      "Section title.",
      "Paragraphs. Start a line with \"- \" to make it a bullet point.",
    ],
  },
  services: {
    diagram: "tile",
    title: "Services: the cards on the home page and each service's own page",
    steps: [
      "Photo: on the card and on the service page.",
      "Title and summary: on the card and the page banner.",
      "Paragraphs and common faults: the body of the service page.",
      "Form label must match one of the Service required choices in Enquiry form.",
    ],
  },
  regions: {
    diagram: "areas",
    title: "Areas we cover: the five London regions and their districts",
    steps: [
      "Region name: the column heading.",
      "Intro: the sentence shown on the Areas page under the region.",
      "Districts: each gets its own page at /areas/<slug>.",
    ],
  },
  faqs: {
    diagram: "faq",
    title: "FAQs: the question list on the home page and the FAQs page",
    steps: ["The heading is edited under Section headings.", "Question and answer. One entry per question."],
  },
  testimonials: {
    diagram: "testimonial",
    title: "Testimonials: the customer feedback cards",
    steps: [
      "Quote.",
      "Name and general location.",
      "Rating: stars out of 5, shown only when Sample content is switched off.",
      "Sample content: tick while the quote is a placeholder; the site then labels the section as sample feedback.",
    ],
  },
  "trust-points": {
    diagram: "strip",
    title: "Trust strip: the four points in the dark band under the hero",
    steps: ["Icon.", "Title.", "Short text."],
  },
  "why-us": {
    diagram: "featureCards",
    title: "Why choose us: the six points on the home and About pages",
    steps: ["Icon.", "Title.", "Text."],
  },
  process: {
    diagram: "steps",
    title: "How it works: the four numbered steps",
    steps: ["Number: from the order of the entries.", "Title.", "Text. The same steps also appear beside the enquiry form."],
  },
  "quote-factors": {
    diagram: "factors",
    title: "Quotations: the numbered list of what affects the cost",
    steps: ["Number: from the order of the entries.", "Title.", "Text."],
  },
};
