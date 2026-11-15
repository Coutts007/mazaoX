import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

const supportsObserver = () => typeof window !== "undefined" && "IntersectionObserver" in window;

/** Fades and lifts its children in the first time they scroll into view. Content is always visible without JS observers (tests, old browsers). */
export function Reveal({ children, delay = 0, className = "", as: Tag = "div" }: { children: ReactNode; delay?: number; className?: string; as?: "div" | "section" }) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(!supportsObserver());
  useEffect(() => {
    if (shown || !ref.current) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setShown(true); io.disconnect(); } }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [shown]);
  const style = { "--delay": `${delay}ms` } as CSSProperties;
  return <Tag ref={ref as never} className={`reveal ${shown ? "in" : ""} ${className}`} style={style}>{children}</Tag>;
}
