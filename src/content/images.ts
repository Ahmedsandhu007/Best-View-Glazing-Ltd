import imagesData from "./images.json";

/**
 * Page photographs, edited under "Photographs" in the CMS. Each holds a site
 * path (/uploads/…) or an https image URL plus the alt text read by screen
 * readers and search engines. Service photos live on each service entry.
 */
export type SiteImage = { src: string; alt: string };
export type ImageKey = keyof typeof imagesData;

export const images = imagesData as Record<ImageKey, SiteImage>;
