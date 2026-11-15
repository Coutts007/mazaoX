const P: Record<string, string> = {
  home: "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10",
  search: "M10.5 17a6.5 6.5 0 100-13 6.5 6.5 0 000 13zM15.5 15.5L20 20",
  orders: "M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6",
  megaphone: "M3 11v3l12 5V6zM15 9a3 3 0 010 6M6 14l1 5h3",
  key: "M14 10a4 4 0 11-1.2-2.8L21 15v3h-3v-2h-2v-2h-2.2",
  farm: "M4 20V9l8-5 8 5v11M9 20v-6h6v6",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  chart: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  users: "M16 20v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM21 20v-1a4 4 0 00-3-3.9M16 4.1a3.5 3.5 0 010 6.8",
  alert: "M12 3l10 18H2zM12 10v5M12 18h.01",
  star: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z",
  log: "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7",
  cart: "M3 4h2l2.4 11h10.2L20 7H6M9 20h.01M17 20h.01",
  bell: "M6 17V11a6 6 0 1112 0v6l2 2H4zM10 21h4",
  lock: "M6 11h12v9H6zM8 11V8a4 4 0 118 0v3",
  pin: "M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11zM12 12a2.5 2.5 0 100-5 2.5 2.5 0 000 5z",
  filter: "M3 5h18l-7 8v6l-4-2v-4z",
  check: "M5 12.5l4.5 4.5L19 7.5",
};

export type IconName = keyof typeof P;

/** Simple outline icons (inherit the text colour). */
export function Icon({ name, size = 22 }: { name: IconName; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={P[name]} />
    </svg>
  );
}
