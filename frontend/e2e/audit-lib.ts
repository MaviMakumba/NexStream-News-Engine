// Sayfa içinde çalışan mobil kullanılabilirlik ölçümleri (tek noktada, hem tarama
// raporu hem regresyon testi aynı fonksiyonu kullanır).
import type { Page } from "@playwright/test";

export interface Issue {
  kind: "overflow" | "tap-target" | "input-zoom" | "tiny-text" | "clipped-text";
  severity: "high" | "med" | "low";
  selector: string;
  text: string;
  detail: string;
}

export async function measurePage(page: Page): Promise<Issue[]> {
  return page.evaluate(() => {
    const out: Issue[] = [] as never[];
    const vw = window.innerWidth;
    const sel = (el: Element) => {
      const id = (el as HTMLElement).id ? `#${(el as HTMLElement).id}` : "";
      const cls = typeof (el as HTMLElement).className === "string"
        ? "." + (el as HTMLElement).className.trim().split(/\s+/).slice(0, 2).join(".") : "";
      return `${el.tagName.toLowerCase()}${id}${cls === "." ? "" : cls}`;
    };
    const txt = (el: Element) => ((el as HTMLElement).innerText || el.getAttribute("aria-label") || el.getAttribute("title") || "").trim().replace(/\s+/g, " ").slice(0, 40);
    const visible = (el: Element) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && parseFloat(cs.opacity) > 0;
    };
    // Kendi kaydırma alanı olan (overflow-x:auto/scroll) bir atanın İÇİNDE mi?
    const inScroller = (el: Element) => {
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if (ox === "auto" || ox === "scroll") return true;
      }
      return false;
    };
    // Sabit bir üst şerit (sticky nav) sayfa kaydırılırken diğer hedefleri örtebilir — burada ölçülmez.
    const all = Array.from(document.body.querySelectorAll("*")).filter(visible);

    // 1) Yatay taşma: body overflow-x:hidden sessizce KIRPAR — sağ kenarı viewport'u aşan elemanları bul.
    const seen = new Set<Element>();
    for (const el of all) {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 1 || r.left < -1) {
        if (inScroller(el)) continue;
        // yalnızca en dıştaki taşan eleman raporlansın (çocukları da taşar)
        let anc = el.parentElement, dup = false;
        while (anc) { if (seen.has(anc)) { dup = true; break; } anc = anc.parentElement; }
        if (dup) continue;
        // position:fixed dekoratif arka plan canvas'ları hariç
        if (el.tagName === "CANVAS") continue;
        // Dekoratif fixed katmanlar (ışık/grid) tıklanmaz, sayfayı kaydırmaz — kırpılması zararsız.
        const cs0 = getComputedStyle(el);
        if (cs0.position === "fixed" && cs0.pointerEvents === "none") continue;
        seen.add(el);
        out.push({ kind: "overflow", severity: "high", selector: sel(el), text: txt(el), detail: `left=${Math.round(r.left)} right=${Math.round(r.right)} vw=${vw}` });
      }
    }

    // 2) Dokunma hedefi. WCAG 2.5.8 AA min 24px; biz 32px altını HATA sayıyoruz
    //    (24 + parmak payı), 32-40px "med" bilgi; Apple/Google önerisi 44/48px.
    const interactive = all.filter((el) => el.matches("a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=tab], summary, label[for]"));
    for (const el of interactive) {
      const r = el.getBoundingClientRect();
      if (el.tagName === "A" && getComputedStyle(el).display === "inline" && el.closest("p, li, span")) continue; // satır-içi metin linkleri hariç
      const m = Math.min(r.width, r.height);
      if (m < 32) out.push({ kind: "tap-target", severity: "high", selector: sel(el), text: txt(el), detail: `${Math.round(r.width)}x${Math.round(r.height)}` });
      else if (m < 40) out.push({ kind: "tap-target", severity: "med", selector: sel(el), text: txt(el), detail: `${Math.round(r.width)}x${Math.round(r.height)}` });
    }

    // 3) iOS Safari <16px input'a odaklanınca sayfayı zoomlar
    for (const el of all.filter((e) => e.matches("input:not([type=checkbox]):not([type=radio]):not([type=hidden]), select, textarea"))) {
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < 16) out.push({ kind: "input-zoom", severity: "med", selector: sel(el), text: txt(el), detail: `font-size ${fs}px` });
    }

    // 4) Çok küçük metin
    const leafText = all.filter((el) => el.children.length === 0 && (el.textContent || "").trim().length > 2);
    for (const el of leafText) {
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < 11) out.push({ kind: "tiny-text", severity: "low", selector: sel(el), text: txt(el), detail: `${fs}px` });
    }

    // 5) Kırpılan metin: içerik kutudan büyük ve overflow gizli, ellipsis yok
    for (const el of leafText) {
      const cs = getComputedStyle(el);
      if (el.scrollWidth > el.clientWidth + 2 && cs.overflowX === "hidden" && cs.textOverflow !== "ellipsis" && cs.whiteSpace === "nowrap") {
        out.push({ kind: "clipped-text", severity: "med", selector: sel(el), text: txt(el), detail: `scrollW=${el.scrollWidth} clientW=${el.clientWidth}` });
      }
    }
    return out;
  });
}
