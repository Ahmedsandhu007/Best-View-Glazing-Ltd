import { Hero } from "@/components/Hero";
import { TrustStrip } from "@/components/TrustStrip";
import { Introduction } from "@/components/Introduction";
import { ServiceGroups } from "@/components/ServiceGroups";
import { CopyBlock } from "@/components/CopyBlock";
import { Signs } from "@/components/Signs";
import { WhyChooseUs } from "@/components/WhyChooseUs";
import { WorkingProcess } from "@/components/WorkingProcess";
import { AreasWeCover } from "@/components/AreasWeCover";
import { CaseStudiesSection } from "@/components/CaseStudiesSection";
import { Testimonials } from "@/components/Testimonials";
import { Pricing } from "@/components/Pricing";
import { BlogTeasers } from "@/components/BlogTeasers";
import { FAQ } from "@/components/FAQ";
import { QuoteSection } from "@/components/QuoteSection";
import { JsonLd } from "@/components/JsonLd";
import { home } from "@/content/site";
import { faqJsonLd } from "@/lib/seo";

/** The home page, block by block in the SEO team's order. Copy lives under Home page and Section headings in the CMS. */
export default function HomePage() {
  const faqs = home.faqs.filter((f) => f.question.trim() && f.answer.trim());
  return (
    <>
      <Hero />
      <TrustStrip />
      <Introduction />
      <ServiceGroups />
      <CopyBlock id="door-repairs" heading={home.doors.heading} paragraphs={home.doors.paragraphs} image="intro" tone="white" />
      <Signs />
      <WhyChooseUs />
      <CopyBlock id="repair-or-replace" heading={home.repairOrReplace.heading} paragraphs={home.repairOrReplace.paragraphs} image="workshop" imageSide="left" tone="ivory" />
      <WorkingProcess tone="white" />
      <Pricing />
      <AreasWeCover detailed publishedOnly />
      <CaseStudiesSection />
      <Testimonials />
      <BlogTeasers />
      {faqs.length > 0 ? <FAQ items={faqs} /> : null}
      <QuoteSection />
      {faqs.length > 0 ? <JsonLd data={faqJsonLd(faqs)} /> : null}
    </>
  );
}
