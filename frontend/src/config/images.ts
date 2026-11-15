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
    "cereals-grains": "/images/categories/cereals-grains.jpg",
    "pulses-legumes": "/images/categories/pulses-legumes.jpg",
    "roots-tubers": "/images/categories/roots-tubers.jpg",
    "vegetables": "/images/categories/vegetables.jpg",
    "fruits": "/images/categories/fruits.jpg",
    "nuts-oilseeds": "/images/categories/nuts-oilseeds.jpg",
    "cash-crops": "/images/categories/cash-crops.jpg",
    "herbs-spices": "/images/categories/herbs-spices.jpg",
    "fodder-forage": "/images/categories/fodder-forage.jpg",
    "flowers-nursery": "/images/categories/flowers-nursery.jpg",
    "livestock": "/images/categories/livestock.jpg",
    "apiculture": "/images/categories/apiculture.jpg",
    "fisheries": "/images/categories/fisheries.jpg",
    "processed-products": "/images/categories/processed-products.jpg",
    "forestry": "/images/categories/forestry.jpg",
  } as Record<string, string>,
};
