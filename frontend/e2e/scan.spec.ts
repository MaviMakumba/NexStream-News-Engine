// Geniş cihaz matrisi TARAMASI (rapor üretir, geçme/kalma kararı vermez).
// Çalıştır: AUDIT_OUT=<dizin> npx playwright test e2e/scan.spec.ts
import { test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { mockApi } from "./mock-api";
import { measurePage } from "./audit-lib";

const OUT = process.env.AUDIT_OUT ?? "test-results/audit";
fs.mkdirSync(path.join(OUT, "shots"), { recursive: true });

const DEVICES = [
  { name: "fold-280", w: 280, h: 653, dpr: 3 },
  { name: "se1-320", w: 320, h: 568, dpr: 2 },
  { name: "android-360", w: 360, h: 640, dpr: 3 },
  { name: "se-375", w: 375, h: 667, dpr: 2 },
  { name: "iphone14-390", w: 390, h: 844, dpr: 3 },
  { name: "pixel7-412", w: 412, h: 915, dpr: 2.6 },
  { name: "promax-430", w: 430, h: 932, dpr: 3 },
  { name: "se-landscape-667", w: 667, h: 375, dpr: 2 },
  { name: "iphone14-landscape-844", w: 844, h: 390, dpr: 3 },
  { name: "ipad-768", w: 768, h: 1024, dpr: 2 },
];
const GUEST = ["/", "/auth/login", "/auth/register", "/auth/forgot-password", "/contact", "/privacy", "/terms", "/security"];
const AUTHED = ["/dashboard", "/dashboard/search", "/dashboard/ask", "/account", "/admin/users", "/admin/usage", "/admin/sponsors", "/admin/contact-messages", "/admin/security"];
const THEMES = ["matrix", "godfather", "cyberpunk", "dune", "starwars", "spiderman", "batman", "wolfenstein", "day", "night"];
const SHOT_DEVICES = new Set(["se1-320", "se-375", "iphone14-390"]);

async function scan(browser: import("@playwright/test").Browser, dev: (typeof DEVICES)[number], route: string, authed: boolean, theme: string, lang: string) {
  const ctx = await browser.newContext({
    viewport: { width: dev.w, height: dev.h }, deviceScaleFactor: dev.dpr, isMobile: true, hasTouch: true,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  });
  const page = await ctx.newPage();
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e.message).slice(0, 160)));
  page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource|WebSocket|ERR_/.test(m.text())) errors.push(m.text().slice(0, 160)); });
  await mockApi(page, authed);
  await page.addInitScript(([t, l, u]) => {
    localStorage.setItem("nxt_theme", t); localStorage.setItem("nxt_lang", l);
    if (u) localStorage.setItem("nxt_user", u);
  }, [theme, lang, authed ? JSON.stringify((await import("./mock-api")).USER) : ""] as const);
  await page.goto(route, { waitUntil: "load" });
  await page.waitForTimeout(1500);
  const issues = await measurePage(page);
  const docOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (SHOT_DEVICES.has(dev.name) && theme === "day" && lang === "TR") {
    await page.screenshot({ path: path.join(OUT, "shots", `${dev.name}${route.replace(/\//g, "_") || "_root"}.png`), fullPage: true });
  }
  await ctx.close();
  fs.appendFileSync(path.join(OUT, "results.jsonl"), JSON.stringify({ dev: dev.name, route, theme, lang, docOverflow, errors, issues }) + "\n");
}

test.describe("matris: cihaz x sayfa (day, TR)", () => {
  for (const dev of DEVICES) {
    for (const route of [...GUEST.map((r) => [r, false] as const), ...AUTHED.map((r) => [r, true] as const)]) {
      test(`${dev.name} ${route[0]}`, async ({ browser }) => { await scan(browser, dev, route[0], route[1], "day", "TR"); });
    }
  }
});

test.describe("matris: tema (320 ve 375)", () => {
  for (const dev of DEVICES.filter((d) => ["se1-320", "se-375"].includes(d.name))) {
    for (const theme of THEMES.filter((t) => t !== "day")) {
      for (const [route, authed] of [["/", false], ["/dashboard", true], ["/account", true]] as const) {
        test(`${dev.name} ${theme} ${route}`, async ({ browser }) => { await scan(browser, dev, route, authed, theme, "TR"); });
      }
    }
  }
});

test.describe("matris: EN dili (320)", () => {
  for (const [route, authed] of [["/", false], ["/dashboard", true], ["/account", true], ["/auth/register", false]] as const) {
    test(`se1-320 EN ${route}`, async ({ browser }) => { await scan(browser, DEVICES[1], route, authed, "day", "EN"); });
  }
});
