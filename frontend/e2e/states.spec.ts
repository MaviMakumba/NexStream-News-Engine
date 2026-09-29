// Etkileşimli durum görüntüleri (menü açık, ayarlar paneli, filtreler...) — insan gözüyle inceleme için.
import { test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { mockApi, USER } from "./mock-api";

const OUT = process.env.AUDIT_OUT ?? "test-results/audit";
fs.mkdirSync(path.join(OUT, "states"), { recursive: true });

for (const [name, w, h] of [["320", 320, 568], ["375", 375, 667], ["412", 412, 915]] as const) {
  test(`states ${name}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    await mockApi(page, true);
    await page.addInitScript((u) => { localStorage.setItem("nxt_theme", "day"); localStorage.setItem("nxt_lang", "TR"); localStorage.setItem("nxt_user", u); }, JSON.stringify(USER));
    const shot = async (n: string) => page.screenshot({ path: path.join(OUT, "states", `${name}-${n}.png`) });
    await page.goto("/dashboard"); await page.waitForTimeout(1500);
    await shot("dashboard-top");
    await page.evaluate(() => window.scrollTo(0, 500)); await page.waitForTimeout(300); await shot("dashboard-scrolled");
    await page.evaluate(() => window.scrollTo(0, 0));
    const burger = page.locator('button[class*="md:hidden"]').first();
    if (await burger.count()) { await burger.click(); await page.waitForTimeout(400); await shot("menu-open"); await burger.click().catch(() => {}); }
    for (const [n, route] of [["landing", "/"], ["account", "/account"], ["search", "/dashboard/search"], ["ask", "/dashboard/ask"], ["login", "/auth/login"]] as const) {
      await page.goto(route); await page.waitForTimeout(1200); await shot(n);
    }
    await ctx.close();
  });
}
