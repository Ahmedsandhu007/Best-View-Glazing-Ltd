/**
 * Business configuration.
 * Keep all company facts here so UI components never hard-code them.
 * Only include details that are genuinely true for the business.
 */
export const site = {
  name: "Best View Glazing Ltd",
  shortName: "Best View Glazing",
  legalLine: "© 2026 Best View Glazing Ltd. All Rights Reserved.",
  tagline: "Professional window and door repair specialists operating throughout Greater London.",
  description:
    "Window and door repair specialists covering Greater London. uPVC, aluminium, timber and sash window repairs, double glazing, locks, handles, hinges and door mechanisms for homes and commercial properties.",
  /** Public URL of the deployed site. Set NEXT_PUBLIC_SITE_URL in production. */
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "https://www.bestviewglazing.co.uk",
  region: "Greater London",
  /** The only enquiry channel is the website form. No phone or email channels are published. */
  enquiryPath: "/contact",
  enquiryFormId: "quote-form",
} as const;

export const navigation = [
  { label: "Home", href: "/" },
  { label: "Our Services", href: "/services" },
  { label: "About Us", href: "/about" },
  { label: "Areas We Cover", href: "/areas" },
  { label: "FAQs", href: "/faqs" },
  { label: "Contact", href: "/contact" },
] as const;

export const legalLinks = [
  { label: "Privacy Policy", href: "/privacy-policy" },
  { label: "Terms & Conditions", href: "/terms" },
] as const;

export const trustPoints = [
  {
    title: "Residential & Commercial",
    text: "Homes, flats, rented property, offices and retail premises across London.",
    icon: "building",
  },
  {
    title: "Experienced Repair Specialists",
    text: "Mechanical, glazing and frame faults diagnosed and repaired rather than replaced where practical.",
    icon: "wrench",
  },
  {
    title: "Transparent Quotations",
    text: "A written quotation that sets out the work and the parts required before anything is agreed.",
    icon: "file",
  },
  {
    title: "Greater London Coverage",
    text: "Central, North, East, South and West London served from one team.",
    icon: "map",
  },
] as const;

export const whyChooseUs = [
  {
    title: "Experienced Repair Approach",
    text: "Our specialists work on the mechanisms, glazing units and frames that fail most often, so faults are identified quickly and the right repair is proposed first time.",
  },
  {
    title: "Residential & Commercial Expertise",
    text: "We look after family homes, flats and managed blocks as well as offices, shops and other commercial buildings, adapting how we work to the property and the people using it.",
  },
  {
    title: "Practical Repair Solutions",
    text: "Where a window or door can be repaired properly, we repair it. Replacement is only suggested when a repair would not give a lasting or cost-effective result.",
  },
  {
    title: "Clear Quotations",
    text: "Every quotation describes the fault, the proposed work and the parts involved in plain English, so you know what you are agreeing to before work begins.",
  },
  {
    title: "Local London Coverage",
    text: "We operate across Greater London rather than a single borough, which means consistent service whether the property is in Croydon, Camden or Canary Wharf.",
  },
  {
    title: "Customer-Focused Service",
    text: "Enquiries are reviewed by people who understand window and door hardware, and we keep you informed from the first message to the finished repair.",
  },
] as const;

export const processSteps = [
  {
    title: "Submit Your Enquiry",
    text: "Complete the website enquiry form and tell us about the window or door problem. Photographs are welcome and help us assess the fault.",
  },
  {
    title: "Review & Assessment",
    text: "Our team reviews the information you have provided and assesses the likely cause, the parts involved and the access required.",
  },
  {
    title: "Quotation",
    text: "You receive a response setting out the relevant repair information together with a clear quotation for the work.",
  },
  {
    title: "Arrange the Repair",
    text: "Once the quotation is agreed, the repair visit is arranged at a time that suits the property and the people in it.",
  },
] as const;

export const quoteFactors = [
  { title: "Window or door type", text: "uPVC, aluminium, timber, sash and composite units all use different hardware and glazing methods." },
  { title: "Nature of the fault", text: "A stiff handle is a different job from a dropped sash, a failed sealed unit or a split frame." },
  { title: "Parts and materials", text: "Some repairs use standard hardware; others need unit-specific or made-to-measure components." },
  { title: "Complexity of the repair", text: "Multi-point mechanisms, period joinery and large glazed units take longer and need more care." },
  { title: "Access and property requirements", text: "Upper floors, restricted access and occupied commercial premises affect how the work is planned." },
] as const;
