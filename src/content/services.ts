import servicesData from "./services.json";
import formData from "./form.json";

export type Service = {
  slug: string;
  title: string;
  /** Short name used in the enquiry form select. */
  formLabel: string;
  /** One-line summary for cards and metadata. */
  summary: string;
  /** Longer copy for the service page. */
  body: string[];
  /** Typical faults handled under this service. */
  faults: string[];
  /** Photo: a site path (/uploads/…) or an https image URL. */
  image: string;
  imageAlt: string;
  /** Lucide icon name used where a photo is not appropriate. */
  icon: string;
  /** SEO keyword phrase used in the page title. */
  seoTitle: string;
};

export const services = servicesData as Service[];

export function findService(slug: string) {
  return services.find((s) => s.slug === slug);
}

/** Options for the enquiry form, edited under "Enquiry form" in the CMS. */
export const serviceFormOptions: readonly string[] = formData.serviceOptions;
export const propertyTypeOptions: readonly string[] = formData.propertyTypeOptions;
export const contactTimeOptions: readonly string[] = formData.contactTimeOptions;
