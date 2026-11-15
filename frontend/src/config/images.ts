/**
 * Site images (NOT user uploads). Drop a file into `frontend/public/images/` using the name below and it appears
 * automatically; a missing file is simply skipped and a plain fallback is shown. Change a path here to use a different
 * file name or format. Produce photos uploaded by farmers are separate and come from the API.
 *
 * Recommended sizes (JPEG/WebP, compress to under ~300 KB):
 *   hero             1920×1080+  wide landscape; a dark scrim is added so white text stays readable
 *   authBackground   1600×1000   behind the login/register card
 *   ctaBand          1600×600    behind the "Grow with MazaoX" band
 *   steps            800×600     one per "How it works" step (optional)
 *   categories       600×600     square-ish, one per category slug
 *   listingPlaceholder 800×600   shown for a listing the farmer has not added photos to
 */
export const SITE_IMAGES = {
  hero: "/images/hero.jpg",
  authBackground: "/images/auth-bg.jpg",
  ctaBand: "/images/cta-band.jpg",
  listingPlaceholder: "/images/listing-placeholder.jpg",
  steps: ["/images/step-1.jpg", "/images/step-2.jpg", "/images/step-3.jpg"],
  /** Keyed by category slug (see the categories your API returns). */
  categories: {
    tomatoes: "/images/categories/tomatoes.jpg",
    kale: "/images/categories/kale.jpg",
    maize: "/images/categories/maize.jpg",
    potatoes: "/images/categories/potatoes.jpg",
    onions: "/images/categories/onions.jpg",
  } as Record<string, string>,
};
