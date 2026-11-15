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

/** Counts up to `to` once visible. Renders the final number immediately when motion is reduced or unsupported. */
export function CountUp({ to, suffix = "" }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduced = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [n, setN] = useState(!supportsObserver() || reduced ? to : 0);
  useEffect(() => {
    if (!supportsObserver() || reduced || !ref.current) return;
    let raf = 0;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (t: number) => {
        const p = Math.min(1, (t - start) / 1100);
        setN(Math.round(to * (1 - Math.pow(1 - p, 3))));
        if (p < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    });
    io.observe(ref.current);
    return () => { io.disconnect(); cancelAnimationFrame(raf); };
  }, [to, reduced]);
  return <span ref={ref} aria-label={`${to}${suffix}`}>{n}{suffix}</span>;
}
