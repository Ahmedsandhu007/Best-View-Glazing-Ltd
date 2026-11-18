import type { Metadata } from "next";
import { Button } from "@/components/ui/Button";

export const metadata: Metadata = { title: "Page not found", robots: { index: false } };

export default function NotFound() {
  return (
    <section className="section bg-ivory">
      <div className="container-site max-w-2xl text-center">
        <p className="eyebrow">Page not found</p>
        <h1 className="mt-3 text-4xl font-bold">We could not find that page</h1>
        <p className="mt-4 text-lg text-muted">
          The address may have changed or been typed incorrectly. The links below will take you back to the main parts of the
          site.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button href="/">Back to the home page</Button>
          <Button href="/services" variant="secondary">
            View our services
          </Button>
        </div>
      </div>
    </section>
  );
}
