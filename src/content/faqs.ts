import faqsData from "./faqs.json";

export type Faq = { slug: string; question: string; answer: string };

export const faqs = faqsData as Faq[];
