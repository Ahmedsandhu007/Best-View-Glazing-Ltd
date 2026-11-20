import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { BackToTop } from "@/components/BackToTop";
import { FloatingWhatsApp } from "@/components/WhatsAppButton";
import { JsonLd } from "@/components/JsonLd";
import { Analytics } from "@/components/Analytics";
import { site } from "@/content/site";
import { organizationJsonLd, websiteJsonLd } from "@/lib/seo";

export default function SiteLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-sm focus:bg-teal focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>
      <Header />
      <main id="main-content" className="flex-1">
        {children}
      </main>
      <Footer />
      <FloatingWhatsApp />
      <BackToTop />
      <JsonLd data={[organizationJsonLd(), websiteJsonLd()]} />
      <Analytics measurementId={site.ga4MeasurementId} />
    </>
  );
}
