// Mobil kullanılabilirlik REGRESYON testi (backend'siz, API taklitli).
// Her UI değişikliğinden sonra: `npm run build && npm run test:mobile`.
// Kurallar: bkz. e2e/audit-lib.ts. Geniş rapor (cihaz x tema x dil) için e2e/scan.spec.ts.
import { test, expect, type Browser } from "@playwright/test";
import { mockApi, USER } from "./mock-api";
import { measurePage } from "./audit-lib";

const WIDTHS = [320, 360, 375, 390, 412, 430];
const GUEST = ["/", "/auth/login", "/auth/register", "/auth/forgot-password", "/contact", "/privacy", "/terms", "/security"];
const AUTHED = ["/dashboard", "/dashboard/search", "/dashboard/ask", "/account", "/admin/users", "/admin/usage", "/admin/sponsors", "/admin/contact-messages", "/admin/security"];

async function open(browser: Browser, w: number, h: number, route: string, authed: boolean, opts: { theme?: string; lang?: string } = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await mockApi(page, authed);
  await page.addInitScript(([t, l, u]) => {
    localStorage.setItem("nxt_theme", t); localStorage.setItem("nxt_lang", l);
    if (u) localStorage.setItem("nxt_user", u);
  }, [opts.theme ?? "day", opts.lang ?? "TR", authed ? JSON.stringify(USER) : ""] as const);
  await page.goto(route, { waitUntil: "load" });
  await page.waitForTimeout(1200);
  return { ctx, page };
}

test("emülasyon gerçekten dokunmatik (pointer: coarse)", async ({ browser }) => {
  const { ctx, page } = await open(browser, 375, 667, "/", false);
  expect(await page.evaluate(() => matchMedia("(pointer: coarse)").matches)).toBe(true);
  await ctx.close();
});

for (const w of WIDTHS) {
  for (const [route, authed] of [...GUEST.map((r) => [r, false] as const), ...AUTHED.map((r) => [r, true] as const)]) {
    test(`${w}px ${route}: taşma/dokunma/zoom sorunu yok`, async ({ browser }) => {
      const { ctx, page } = await open(browser, w, 800, route, authed);
      const blocking = (await measurePage(page)).filter((i) => i.severity === "high" || i.kind === "input-zoom" || i.kind === "overflow");
      await ctx.close();
      expect(blocking, JSON.stringify(blocking, null, 1)).toEqual([]);
    });
  }
}

// md kırılımı (>=768px) masaüstü navbar'ına geçer: iPad ve YATAY telefon bu düzene düşer,
// ama parmakla kullanılır — dokunma hedefleri orada da yeterli olmalı.
for (const [w, h, label] of [[768, 1024, "iPad dikey"], [844, 390, "iPhone yatay"], [667, 375, "SE yatay"]] as const) {
  for (const [route, authed] of [["/", false], ["/dashboard", true], ["/account", true]] as const) {
    test(`${label} ${w}x${h} ${route}: temiz`, async ({ browser }) => {
      const { ctx, page } = await open(browser, w, h, route, authed);
      const blocking = (await measurePage(page)).filter((i) => i.severity === "high" || i.kind === "input-zoom" || i.kind === "overflow");
      await ctx.close();
      expect(blocking, JSON.stringify(blocking, null, 1)).toEqual([]);
    });
  }
}

for (const theme of ["matrix", "night", "starwars", "wolfenstein"]) {
  test(`320px ${theme} teması: anasayfa + dashboard temiz`, async ({ browser }) => {
    for (const [route, authed] of [["/", false], ["/dashboard", true]] as const) {
      const { ctx, page } = await open(browser, 320, 568, route, authed, { theme });
      const blocking = (await measurePage(page)).filter((i) => i.severity === "high" || i.kind === "input-zoom" || i.kind === "overflow");
      await ctx.close();
      expect(blocking, `${theme} ${route}: ${JSON.stringify(blocking)}`).toEqual([]);
    }
  });
}

test("320px EN: anasayfa ve kayıt temiz", async ({ browser }) => {
  for (const route of ["/", "/auth/register"]) {
    const { ctx, page } = await open(browser, 320, 568, route, false, { lang: "EN" });
    const blocking = (await measurePage(page)).filter((i) => i.severity === "high" || i.kind === "input-zoom" || i.kind === "overflow");
    await ctx.close();
    expect(blocking, `${route}: ${JSON.stringify(blocking)}`).toEqual([]);
  }
});

test("performans varsayılanı: zayıf dokunmatik cihazda low, güçlüde high, kayıtlı tercih kazanır", async ({ browser }) => {
  const run = async (cores: number, stored?: string) => {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 667 }, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    await mockApi(page, false);
    await page.addInitScript(([c, s]) => {
      Object.defineProperty(navigator, "hardwareConcurrency", { get: () => c });
      if (s) localStorage.setItem("nxt_perf", s);
    }, [cores, stored ?? ""] as const);
    await page.goto("/");
    await page.waitForTimeout(600);
    const perf = await page.evaluate(() => document.documentElement.dataset.perf);
    await ctx.close();
    return perf;
  };
  expect(await run(2)).toBe("low");
  expect(await run(8)).toBe("high");
  expect(await run(2, "high")).toBe("high");
});

test("mobil menü: opak, kısa ekranda kaydırılabilir, çıkış butonuna ulaşılır", async ({ browser }) => {
  const { ctx, page } = await open(browser, 320, 568, "/dashboard", true);
  await page.locator('button[class*="md:hidden"]').first().click();
  const panel = page.locator(".mobile-menu-panel");
  await expect(panel).toBeVisible();
  const bg = await panel.evaluate((el) => getComputedStyle(el).backgroundColor);
  const alpha = bg.startsWith("rgba") ? parseFloat(bg.split(",")[3]) : 1;
  expect(alpha, `panel arka planı saydam: ${bg}`).toBe(1);
  const logout = panel.getByRole("button", { name: /Çıkış|Logout|Sign out/i });
  await logout.scrollIntoViewIfNeeded();
  const box = await logout.boundingBox();
  const vh = page.viewportSize()!.height;
  expect(box && box.y >= 0 && box.y + box.height <= vh, `çıkış butonu görünür alanda değil: ${JSON.stringify(box)}`).toBe(true);
  expect(box!.height).toBeGreaterThanOrEqual(40);
  await ctx.close();
});

test("sohbet ekranı: mesaj kutusu 568px yüksekliğe sığar", async ({ browser }) => {
  const { ctx, page } = await open(browser, 320, 568, "/dashboard/ask", true);
  const input = page.locator(".chat-shell input").last();
  const box = await input.boundingBox();
  expect(box && box.y + box.height <= 568, `input alt sınırı: ${JSON.stringify(box)}`).toBe(true);
  await ctx.close();
});
