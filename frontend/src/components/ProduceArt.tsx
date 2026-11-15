const ART: Record<string, { emoji: string; bg: string }> = {
  tomatoes: { emoji: "🍅", bg: "linear-gradient(135deg,#ffe0d6,#ffc9b8)" },
  kale: { emoji: "🥬", bg: "linear-gradient(135deg,#ddf2c9,#bfe5a0)" },
  maize: { emoji: "🌽", bg: "linear-gradient(135deg,#fff1bf,#ffe389)" },
  potatoes: { emoji: "🥔", bg: "linear-gradient(135deg,#f3e3cf,#e6c9a3)" },
  onions: { emoji: "🧅", bg: "linear-gradient(135deg,#f6e3ee,#ecc6dc)" },
};
const FALLBACK = { emoji: "🧺", bg: "linear-gradient(135deg,#e6f1dc,#cfe6bd)" };

export function artFor(slug?: string) {
  return (slug && ART[slug]) || FALLBACK;
}

/** Placeholder illustration used when a listing has no photo. */
export function ProduceArt({ slug, size = 56, className = "" }: { slug?: string; size?: number; className?: string }) {
  const a = artFor(slug);
  return (
    <div className={`art ${className}`} style={{ background: a.bg, fontSize: size }} aria-hidden="true">
      {a.emoji}
    </div>
  );
}
