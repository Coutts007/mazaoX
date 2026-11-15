import { useEffect, useState, type CSSProperties } from "react";

const cache = new Map<string, boolean>();

/** True once `src` is known to load. Missing files (or the SPA's HTML fallback) resolve to false so callers can show a fallback. */
export function useImageAvailable(src?: string | null): boolean {
  const [ok, setOk] = useState<boolean>(src ? cache.get(src) ?? false : false);
  useEffect(() => {
    if (!src) { setOk(false); return; }
    if (cache.has(src)) { setOk(cache.get(src)!); return; }
    let alive = true;
    const img = new Image();
    img.onload = () => { cache.set(src, true); if (alive) setOk(true); };
    img.onerror = () => { cache.set(src, false); if (alive) setOk(false); };
    img.src = src;
    return () => { alive = false; };
  }, [src]);
  return ok;
}

/** An <img> that renders nothing when the file is missing. */
export function SiteImage({ src, alt = "", className, style }: { src?: string | null; alt?: string; className?: string; style?: CSSProperties }) {
  const ok = useImageAvailable(src);
  return ok && src ? <img src={src} alt={alt} className={className} style={style} loading="lazy" /> : null;
}

/** Inline style that sets a background image only when the file exists. */
export function useBackground(src?: string | null): CSSProperties | undefined {
  const ok = useImageAvailable(src);
  return ok && src ? { backgroundImage: `url(${src})` } : undefined;
}
