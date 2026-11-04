/**
 * PLACEHOLDER TESTIMONIALS
 * ------------------------------------------------------------------
 * These entries are illustrative placeholders written for development.
 * They are NOT real customers and must be replaced with genuine,
 * permissioned feedback before the site goes live.
 *
 * To replace: edit the entries below and set `placeholder: false` once
 * the content is genuine. While any entry is a placeholder the UI labels
 * the section as sample content and shows no star ratings. Add a
 * `rating` only when the customer actually gave one.
 */
export type Testimonial = {
  name: string;
  location: string;
  quote: string;
  /** Star rating 1–5. Only rendered when the entry is genuine. */
  rating?: number;
  placeholder: boolean;
};

export const testimonials: Testimonial[] = [
  {
    name: "Sample customer",
    location: "Islington, North London",
    quote:
      "Example feedback: a dropped uPVC sash and two failed hinges were diagnosed from the photographs we sent, quoted clearly and repaired in a single visit.",
    placeholder: true,
  },
  {
    name: "Sample customer",
    location: "Greenwich, South London",
    quote:
      "Example feedback: misted double glazing in a bay window replaced with new sealed units while keeping the original frames. Tidy work and good communication.",
    placeholder: true,
  },
  {
    name: "Sample customer",
    location: "Hammersmith, West London",
    quote:
      "Example feedback: a commercial front door with a failing multi-point lock was repaired outside trading hours with no disruption to staff or customers.",
    placeholder: true,
  },
];

export const hasPlaceholderTestimonials = testimonials.some((t) => t.placeholder);
