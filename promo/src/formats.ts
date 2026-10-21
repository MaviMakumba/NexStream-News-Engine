// Yatay (masaüstü) ve dikey (mobil) kurgu farkları TEK yerde: boyutlar, yazı ölçüleri,
// alt yazının yeri ve kameranın içeriği yerleştirebileceği "güvenli alan".

export type FormatId = "desktop" | "mobile";

export interface FormatSpec {
  width: number;
  height: number;
  /** Alt yazı bandı: güvenli alanın dışında kalır, odaklanan içerik onun altında kalmaz. */
  caption: { fontSize: number; align: "left" | "center"; top: number | null; bottom: number | null; side: number; maxWidth: number };
  label: { fontSize: number };
  /** Tema geçidindeki tema adı rozetinin yeri (alt yazıyla çakışmayacak köşe). */
  themeTag: { top?: number; bottom?: number; right?: number; left?: number };
  /** Kameranın odak dikdörtgenini yerleştirdiği bölge (piksel, kare koordinatı). */
  safe: { x: number; y: number; w: number; h: number };
  logo: { icon: number; word: number; slogan: number; direction: "row" | "column" };
  hook: { headline: number; title: number };
  cursor: "pointer" | "touch";
  /** Dar kadraj: etiketler içeriğin yanına değil üstüne/altına konur. */
  narrow: boolean;
}

export const FORMATS: Record<FormatId, FormatSpec> = {
  desktop: {
    width: 1920,
    height: 1080,
    caption: { fontSize: 54, align: "left", top: null, bottom: 64, side: 80, maxWidth: 1640 },
    label: { fontSize: 25 },
    themeTag: { top: 150, right: 70 },
    safe: { x: 60, y: 40, w: 1800, h: 790 },
    logo: { icon: 170, word: 132, slogan: 46, direction: "row" },
    hook: { headline: 30, title: 92 },
    cursor: "pointer",
    narrow: false,
  },
  mobile: {
    width: 1080,
    height: 1920,
    caption: { fontSize: 60, align: "center", top: 110, bottom: null, side: 60, maxWidth: 960 },
    label: { fontSize: 30 },
    themeTag: { bottom: 150, left: 0, right: 0 },
    safe: { x: 30, y: 430, w: 1020, h: 1420 },
    logo: { icon: 220, word: 140, slogan: 52, direction: "column" },
    hook: { headline: 30, title: 96 },
    cursor: "touch",
    narrow: true,
  },
};
