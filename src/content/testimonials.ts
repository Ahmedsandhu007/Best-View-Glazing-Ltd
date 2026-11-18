import testimonialsData from "./testimonials.json";

/**
 * Testimonials are edited in the CMS. An entry marked `placeholder` is sample
 * copy: the section labels it as such and shows no stars until it is replaced.
 */
export type Testimonial = {
  slug: string;
  name: string;
  location: string;
  quote: string;
  /** Star rating 1–5. Only rendered when the entry is genuine. */
  rating?: number;
  placeholder: boolean;
};

export const testimonials = testimonialsData as Testimonial[];

export const hasPlaceholderTestimonials = testimonials.some((t) => t.placeholder);
