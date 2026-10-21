// Sitenin kendi yazı tipleri (frontend/app/layout.tsx): gövde Inter, logo/başlık Newsreader.
// latin-ext: Türkçe ğ/ş/ı/İ için şart.
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadNewsreader } from "@remotion/google-fonts/Newsreader";

export const INTER = loadInter("normal", { weights: ["400", "500", "600", "700", "800", "900"], subsets: ["latin", "latin-ext"] }).fontFamily;
export const NEWSREADER = loadNewsreader("normal", { weights: ["600", "700", "800"], subsets: ["latin", "latin-ext"] }).fontFamily;
