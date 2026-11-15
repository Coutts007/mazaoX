import { SITE_IMAGES } from "../config/images";
import { SiteImage, useImageAvailable } from "./SiteImage";

/** Category tint used behind the fallback so cards without any image still look intentional. */
const TINT: Record<string, string> = {
  "cereals-grains": "#f1e8c4", "pulses-legumes": "#eadfce", "roots-tubers": "#eadfce", vegetables: "#dfe9d3", fruits: "#f6e3c8",
  "nuts-oilseeds": "#ecdfc8", "cash-crops": "#dde7d3", "herbs-spices": "#e0ead0", "fodder-forage": "#e3e9c9", "flowers-nursery": "#f3dde4",
  livestock: "#eadccf", apiculture: "#f5e6b8", fisheries: "#d8e6ee", "processed-products": "#eadfce", forestry: "#d9e2cf",
};

/**
 * Stand-in shown when a listing has no uploaded photo: your category image, then your generic placeholder,
 * then a plain tinted block with the category name. Configure the images in `src/config/images.ts`.
 */
export function ProduceArt({ slug, name, className = "" }: { slug?: string; name?: string; size?: number; className?: string }) {
  const catSrc = slug ? SITE_IMAGES.categories[slug] : undefined;
  const hasCat = useImageAvailable(catSrc);
  const hasGeneric = useImageAvailable(SITE_IMAGES.listingPlaceholder);
  const src = hasCat ? catSrc : hasGeneric ? SITE_IMAGES.listingPlaceholder : null;
  return (
    <div className={`art ${className}`} style={{ background: TINT[slug ?? ""] ?? "#e4e8da" }} aria-hidden="true">
      {src ? <SiteImage src={src} className="art-img" /> : <span className="art-label">{name ?? slug ?? ""}</span>}
    </div>
  );
}
