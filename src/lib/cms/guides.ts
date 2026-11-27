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
      "Profile links: the Google Business Profile, Facebook and other profile addresses, published as sameAs in the structured data.",
      "Tracking: paste the GA4 Measurement ID, the Google Tag Manager container ID, the Ahrefs key and the Search Console and Bing verification codes here, then publish. Empty fields add nothing to the site.",
    ],
  },
  home: {
    diagram: "homeHero",
    title: "Home page: every block of copy, top to bottom",
    steps: [
      "Hero: small label, headline, the paragraphs under it and the two buttons (the second can be a phone number: tel:+44…).",
      "Introduction: label, title, paragraphs and button.",
      "Service groups: four cards; link each service inside the text as [name](/services/slug).",
      "Door repairs, Signs, Repair or replace and the Cost table are plain text blocks; a block with no text is hidden.",
      "Home page FAQs are separate from the FAQs page list. Links are allowed in answers.",
      "Headings for the shared blocks (services, why us, how it works, areas, cost, FAQs, quote) are under Section headings.",
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
  contact: {
    diagram: "contact",
    title: "Contact page: details, WhatsApp button and map",
    steps: [
      "Heading and intro line, then the WhatsApp button (number, button text and the message it starts with).",
      "Phone, email, address and opening hours, one line each. Empty lines are not shown.",
      "The map, from an address or a pasted Google Maps embed address.",
      "The floating WhatsApp button that sits in the corner of every page.",
      "Opening hours for Google: the same hours in Google's format (Mo-Fr 08:00-18:00), published in the structured data.",
    ],
  },
  form: {
    diagram: "form",
    title: "Enquiry form: the dropdown choices",
    steps: [
      "Property type: the first dropdown.",
      "Service required: the second dropdown. Keep each service's Form label in Services matching one of these.",
      "Preferred contact time: the third dropdown.",
      "Wording: the line under the Postcode box, and the optional outside-area notice (off while it is empty).",
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
  "service-page": {
    diagram: "hero",
    title: "Service page blocks: what every service page shows unless a service says otherwise",
    steps: [
      "The quote form in the banner and the Call / WhatsApp bar on phones: on or off site-wide.",
      "Why choose us, Benefits, Our process, What affects the cost: a default switch and heading each; the points come from the matching site-wide lists.",
      "Any service can switch a block on or off and give it its own heading, intro or points under its Optional blocks.",
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
    title: "Areas we cover: the regions on the Areas page",
    steps: [
      "Region name: the column heading. Regions outside London are fine.",
      "Intro: the sentence shown on the Areas page under the region.",
      "The towns and districts in each column are edited under Area pages, where each has its own Publish page switch.",
    ],
  },
  "area-pages": {
    diagram: "areas",
    title: "Area pages: one entry per town or district",
    steps: [
      "Name and region put the town in its column on the Areas page.",
      "Write the page first: H1, intro, content sections with their own H2s, nearby places, questions and answers, photo, SEO title and meta description.",
      "Then switch Publish page on and publish: the page goes live at /areas/<address>, is linked and joins the sitemap. Off = no page and the address redirects to /areas.",
    ],
  },
  redirects: {
    diagram: "redirects",
    title: "Redirects: old addresses that send visitors to the new page",
    steps: [
      "Old address: the page that no longer exists, e.g. /services/old-name.",
      "New address: where visitors (and Google) should land instead.",
      "Added for you whenever a page address is changed in the CMS; add your own when you delete a page.",
    ],
  },
  posts: {
    diagram: "blogCard",
    title: "Blog articles: the cards on the Blog page and home page, and each article",
    steps: [
      "Picture: on the card and at the top of the article.",
      "Category, date and reading time.",
      "Title and summary.",
      "Article: one text box for the whole piece. Paste it from Google Docs; headings, bullets, bold and links are kept. Use Insert image for pictures.",
    ],
  },
  "case-studies": {
    diagram: "caseStudy",
    title: "Case studies: the project cards and each case-study page",
    steps: [
      "Picture, with the category badge on it. The category is also a filter button on the Case Studies page.",
      "Title and location.",
      "Summary on the card; the description and write-up on the page.",
      "Results: the three numbers shown on the card and the page.",
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
