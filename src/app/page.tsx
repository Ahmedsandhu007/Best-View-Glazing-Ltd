import { Hero } from "@/components/Hero";
import { TrustStrip } from "@/components/TrustStrip";
import { Introduction } from "@/components/Introduction";
import { Services } from "@/components/Services";
import { WhyChooseUs } from "@/components/WhyChooseUs";
import { WorkingProcess } from "@/components/WorkingProcess";
import { AreasWeCover } from "@/components/AreasWeCover";
import { Testimonials } from "@/components/Testimonials";
import { Pricing } from "@/components/Pricing";
import { FAQ } from "@/components/FAQ";
import { QuoteSection } from "@/components/QuoteSection";
import { JsonLd } from "@/components/JsonLd";
import { faqs } from "@/content/faqs";
import { faqJsonLd } from "@/lib/seo";

export default function HomePage() {
  return (
    <>
      <Hero />
      <TrustStrip />
      <Introduction />
      <Services />
      <WhyChooseUs />
      <WorkingProcess />
      <AreasWeCover />
      <Testimonials />
      <Pricing />
      <FAQ items={faqs} />
      <QuoteSection />
      <JsonLd data={faqJsonLd(faqs)} />
    </>
  );
}
