// Tanıtım videosunun görüntülerini sitenin GERÇEK arayüzünden üretir.
//
// Ön koşul: frontend derlenmiş ve 3100'de çalışıyor olmalı:
//   cd frontend; npm run build; npx next start --port 3100
// Sonra: cd promo; npm run capture            (hepsi)
//        npm run capture -- TR desktop        (tek varyant)
//
// Backend gerekmez: API (localhost:8000) ve /ws/feed WebSocket'i taklit edilir
// (e2e/mock-api.ts deseni), veri kurgusaldır (mock-data.mjs). Çıktı:
//   public/captures/<lang>-<format>/*.jpg|png + manifest.json
// manifest'teki dikdörtgenler CSS pikseli, sayfa koordinatı (scroll dahil);
// Remotion etiket/imleç yerlerini oradan hesaplar.

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { buildData } from "./mock-data.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROMO = path.resolve(HERE, "..");
const REPO = path.resolve(PROMO, "..");
const OUT_ROOT = path.join(PROMO, "public", "captures");
const SITE = process.env.SITE_URL ?? "http://localhost:3100";
const PYTHON = path.join(REPO, "venv", "Scripts", "python.exe");

const FORMATS = {
  desktop: { viewport: { width: 1440, height: 810 }, dpr: 2, mobile: false, touch: false, emailWidth: 640 },
  // isMobile KAPALI: Playwright mobil emülasyonda tam sayfa görüntüsünü farklı yerleşimle
  // alıyor (ölçülen konumlar ~110px kayıyordu). hasTouch yine "pointer: coarse" verir.
  mobile: { viewport: { width: 390, height: 693 }, dpr: 3, mobile: false, touch: true, emailWidth: 390 },
};
// Tema geçidinin sırası videodakiyle aynı; son tema (day) sonraki sahneye bağlanır.
const THEMES = ["matrix", "godfather", "cyberpunk", "dune", "starwars", "spiderman", "batman", "wolfenstein", "night", "day"];
const THEME_FRAMES = 16;
const FRAME_MS = 1000 / 30;

// ── tarayıcı ────────────────────────────────────────────────────────────────

function findChrome() {
  if (process.env.PW_CHROME) return process.env.PW_CHROME;
  const base = path.join(process.env.LOCALAPPDATA ?? "", "ms-playwright");
  if (!fs.existsSync(base)) return undefined;
  const dirs = fs.readdirSync(base).filter((d) => /^chromium-\d+$/.test(d)).sort((a, b) => Number(b.split("-")[1]) - Number(a.split("-")[1]));
  for (const d of dirs) {
    const exe = path.join(base, d, "chrome-win64", "chrome.exe");
    if (fs.existsSync(exe)) return exe;
  }
  return undefined;
}

// Sayfaya enjekte edilen DOM yardımcıları: elemanları gerçek bileşen yapısından bulur,
// sayfa koordinatında dikdörtgen döndürür.
const DOM_HELPERS = () => {
  const r = (el) => {
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return { x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height };
  };
  const textBox = (input) => {
    const cs = getComputedStyle(input);
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const b = r(input);
    const padL = parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth);
    return { x: b.x + padL, y: b.y, w: ctx.measureText(input.value).width, h: b.h, chars: input.value.length };
  };
  const shell = () => {
    const main = document.querySelector("main");
    const live = main?.previousElementSibling;
    const market = live?.previousElementSibling;
    const nav = market?.previousElementSibling;
    return { main, live, market, nav };
  };
  window.__nx = {
    r,
    feed() {
      const { main, live, market, nav } = shell();
      const filters = main.querySelector("select.input")?.parentElement;
      const trending = filters?.previousElementSibling;
      const cards = [...main.querySelectorAll("article.card")];
      return { nav: r(nav), market: r(market), live: r(live), trending: r(trending), filters: r(filters), cards: cards.slice(0, 5).map(r) };
    },
    card(i) {
      const c = [...document.querySelectorAll("main article.card")][i];
      const meta = c.children[0];
      const right = meta.lastElementChild;
      const divs = [...c.querySelectorAll(":scope > div")];
      const chips = divs.find((d) => d.querySelector("button.badge"));
      const footer = divs.find((d) => d.querySelector("button.icon-chip"));
      const after = divs.slice(divs.indexOf(footer) + 1);
      const btns = [...footer.querySelectorAll("button.icon-chip")];
      return {
        card: r(c), meta: r(meta), source: r(meta.children[0]), time: r(meta.children[2]), topic: r(meta.children[3]),
        sentiment: r(right.previousElementSibling), corroboration: r(right.children[0]), trust: r(right.children[1]),
        title: r(c.querySelector(":scope > a")), chips: r(chips), footer: r(footer),
        buttons: { related: r(btns[0]), sources: r(btns[1]), ask: r(btns[2]), listen: r(btns[3]), save: r(btns[4]) },
        panels: after.map(r),
      };
    },
    userMenu() {
      const nav = shell().nav ?? document.querySelector("nav");
      // görünür son buton: masaüstünde hesap menüsü, mobilde hamburger (gizli olanın
      // dikdörtgeni 0x0 — sol üst köşeyi gösterirdi)
      const btns = [...(nav?.querySelectorAll("button") ?? [])].filter((b) => b.getBoundingClientRect().width > 0);
      return r(btns[btns.length - 1]);
    },
    navLink(href) { return r(document.querySelector(`a[href="${href}"]`)); },
    search() {
      const main = document.querySelector("main");
      const input = main.querySelector("input");
      const button = main.querySelector("button.btn-primary");
      const results = [...main.querySelectorAll(".card")];
      return { input: r(input), text: input.value ? textBox(input) : null, button: r(button), results: results.map(r),
        scores: results.map((c) => r([...c.querySelectorAll(".badge")].pop())) };
    },
    ask() {
      const input = document.querySelector("form.chat-form input");
      const send = document.querySelector("form.chat-form button");
      const msgs = [...document.querySelectorAll(".chat-messages > div")].filter((d) => d.querySelector(".card-sm"));
      const out = { input: r(input), text: input.value ? textBox(input) : null, send: r(send), user: r(msgs[0]?.querySelector(".card-sm")) };
      const ans = msgs[1]?.querySelector(".card-sm");
      if (ans) {
        const p = ans.querySelector("p");
        const kids = [...ans.children];
        out.answer = { bubble: r(ans), text: r(p), lineHeight: parseFloat(getComputedStyle(p).lineHeight),
          badges: r(kids[1]), sources: r(kids[2]), alert: r(kids[3]) };
      }
      return out;
    },
    account() {
      const cards = [...document.querySelectorAll(".card")].filter((c) => !c.closest("article") && c.tagName !== "ARTICLE");
      const nl = document.getElementById("newsletter");
      const topicBtns = nl ? [...nl.querySelectorAll("button.badge")] : [];
      const kwInput = nl?.querySelector('input[type="text"]');
      return {
        page: { w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight },
        sections: cards.map((c) => ({ title: (c.querySelector("h2")?.textContent ?? "").trim(), rect: r(c) })),
        newsletter: r(nl),
        topics: Object.fromEntries(topicBtns.map((b) => [b.textContent.trim(), r(b)])),
        keyword: r(kwInput), keywordText: kwInput?.value ? textBox(kwInput) : null,
        frequency: nl ? [...nl.querySelectorAll('button[type="button"]:not(.badge)')].slice(0, 3).map(r) : [],
        save: r(nl?.querySelector('button.btn-primary:not([type="button"])')),
      };
    },
  };
};

// ── taklit API ──────────────────────────────────────────────────────────────

function createMockState(data, opts = {}) {
  return {
    saved: new Set(opts.saved ?? [4, 7]),
    newsletter: { subscribed: false, email: data.user.email, frequency: "daily", topics: [], sources: [], keywords: [], language: data.lang },
    askGate: null,
  };
}

async function respond(data, state, url, method, body) {
  const p = url.pathname.replace(/\/$/, "") || "/";
  const byId = (id) => data.articles.find((a) => a.id === id);
  if (p === "/auth/me") return data.user;
  if (p === "/api/v1/news/trending") return data.trending;
  if (p === "/api/v1/news/sources") return data.sources;
  if (p === "/api/v1/news/ask") {
    if (state.askGate) await state.askGate.promise;
    return data.ask;
  }
  if (p.startsWith("/api/v1/news/search") || p === "/news/search") return data.search;
  if (p.endsWith("/related")) return data.related;
  if (p.endsWith("/sources")) return data.storySources;
  if (p === "/api/v1/news") return { items: data.articles, next_cursor: null, count: data.articles.length };
  if (p === "/account/usage") return data.usage;
  if (p === "/account/api-key") return { api_key: null, has_api_key: true };
  if (p === "/account/saved") return [...state.saved].map(byId).filter(Boolean);
  const savedMatch = p.match(/^\/account\/saved\/(\d+)$/);
  if (savedMatch) {
    if (method === "POST") state.saved.add(Number(savedMatch[1]));
    if (method === "DELETE") state.saved.delete(Number(savedMatch[1]));
    return { success: true };
  }
  if (p === "/account/newsletter") return state.newsletter;
  if (p === "/subscriptions" && method === "POST") {
    state.newsletter = { ...state.newsletter, ...body, subscribed: true };
    return { success: true, message: "ok" };
  }
  if (p === "/billing/config") return { dev_mode: false, stripe_configured: false };
  if (p === "/market/ticker") return data.market;
  return method === "GET" ? {} : { success: true };
}

async function newPage(browser, fmt, data, { theme = "day", dpr, state, history } = {}) {
  const f = FORMATS[fmt];
  const ctx = await browser.newContext({
    viewport: f.viewport, deviceScaleFactor: dpr ?? f.dpr, isMobile: f.mobile, hasTouch: f.touch,
    locale: data.lang === "TR" ? "tr-TR" : "en-US", reducedMotion: "no-preference",
  });
  const page = await ctx.newPage();
  const st = state ?? createMockState(data);
  await page.route(/localhost:8000/, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (url.pathname.endsWith(".xml")) return route.fulfill({ status: 200, contentType: "application/rss+xml", body: '<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>' });
    let body = null;
    try { body = req.postDataJSON(); } catch { /* gövdesiz */ }
    const json = await respond(data, st, url, req.method(), body);
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
  });
  // /ws/feed: sunucuya bağlanmadan "live" — haber göndermek için page.__ws kullanılır.
  let wsResolve;
  const wsReady = new Promise((res) => { wsResolve = res; });
  await page.routeWebSocket(/\/ws\/feed/, (ws) => wsResolve(ws));
  await page.addInitScript(DOM_HELPERS);
  await page.addInitScript(([t, l, u, h]) => {
    localStorage.setItem("nxt_theme", t);
    localStorage.setItem("nxt_lang", l);
    localStorage.setItem("nxt_perf", "high");
    localStorage.setItem("nxt_user", u);
    if (h) localStorage.setItem("nxt_search_history", JSON.stringify([h]));
    // Dinle: başsız tarayıcıda ses yok — konuşma durumu sürsün diye speak() sessiz.
    if ("speechSynthesis" in window) window.speechSynthesis.speak = () => {};
  }, [theme, data.lang, JSON.stringify(data.user), history ?? ""]);
  return { ctx, page, state: st, ws: wsReady };
}

const settle = (page, ms = 900) => page.waitForTimeout(ms);

/**
 * Uzun sayfa görüntüsü için görünümü büyütür. `fullPage: true` KULLANILMAZ: Playwright tam
 * sayfa çekerken dokunmatik emülasyonu düşürüyor → mobilde "pointer: coarse" boşlukları
 * kaybolup içerik ölçülen konumlardan ~110px kayıyordu. Ölçümler de bu görünümde yapılır.
 */
async function tallViewport(page, fmt, height) {
  await page.setViewportSize({ width: FORMATS[fmt].viewport.width, height: Math.ceil(height) });
  await settle(page, 400);
}
const jpg = (page, file, opts = {}) => page.screenshot({ path: file, type: "jpeg", quality: 90, animations: "disabled", caret: "hide", ...opts });

// ── sahneler ────────────────────────────────────────────────────────────────

/** 3. sahne: haberler sayfası her temada; canvas efekti Playwright clock ile kare kare. */
async function captureThemes(browser, fmt, data, out, manifest) {
  const f = FORMATS[fmt];
  const dpr = fmt === "desktop" ? 1920 / f.viewport.width : 1080 / f.viewport.width;
  for (const theme of THEMES) {
    const { ctx, page } = await newPage(browser, fmt, data, { theme, dpr });
    await page.clock.install();
    await page.goto(`${SITE}/dashboard`, { waitUntil: "load" });
    await page.clock.runFor(1500);
    await page.waitForSelector("main article.card");
    await page.clock.runFor(2500); // efekt parçacıkları ekranı doldursun
    const dir = path.join(out, "themes", theme);
    fs.mkdirSync(dir, { recursive: true });
    for (let i = 0; i < THEME_FRAMES; i++) {
      await page.clock.runFor(FRAME_MS);
      await page.screenshot({ path: path.join(dir, `${String(i).padStart(2, "0")}.jpg`), type: "jpeg", quality: 88, caret: "hide" });
    }
    await ctx.close();
  }
  manifest.themes = { order: THEMES, frames: THEME_FRAMES, scale: dpr };
}

/** 4-5. sahne: akış (canlı haber düşer) + haber kartı etkileşimleri. */
async function captureFeedAndCard(browser, fmt, data, out, manifest) {
  const f = FORMATS[fmt];
  const { ctx, page, ws } = await newPage(browser, fmt, data);
  await page.goto(`${SITE}/dashboard`, { waitUntil: "load" });
  await page.waitForSelector("main article.card");
  await settle(page, 1500);
  const clipH = fmt === "desktop" ? 1700 : 2400;
  await tallViewport(page, fmt, clipH);
  const shot = (name) => jpg(page, path.join(out, `${name}.jpg`));

  await shot("feed-before");
  const before = await page.evaluate(() => window.__nx.feed());

  const socket = await ws;
  socket.send(JSON.stringify({ type: "article", data: data.live }));
  await settle(page, 1200);
  await shot("feed-after");
  const after = await page.evaluate(() => window.__nx.feed());

  // Kahraman kart: canlı haberin altındaki (rozetleri tam) ilk haber.
  const HERO = 1;
  const card = (i = HERO) => page.evaluate((k) => window.__nx.card(k), i);
  const states = { base: await card() };
  const btn = (k) => page.locator("main article.card").nth(HERO).locator("button.icon-chip").nth(k);

  await btn(0).click(); await settle(page);
  await shot("card-related"); states.related = await card();
  await btn(1).click(); await settle(page);
  await shot("card-sources"); states.sources = await card();
  await btn(3).click(); await settle(page, 500);
  await shot("card-listen"); states.listen = await card();
  await btn(4).click(); await settle(page, 700);
  await shot("card-saved"); states.saved = await card();
  const userMenu = await page.evaluate(() => window.__nx.userMenu());
  const navLinks = await page.evaluate(() => ({ search: window.__nx.navLink("/dashboard/search"), ask: window.__nx.navLink("/dashboard/ask") }));

  manifest.feed = { clipHeight: clipH, before, after };
  manifest.card = { hero: HERO, states, userMenu, navLinks };
  await ctx.close();
}

/** 6. sahne: habere özel Soru Sor. Sohbet düzeni pencereden biraz uzun; cevap gelince
 *  sayfa kendiliğinden en alta kayıyor — tüm kareler aynı (en alt) kaydırmada alınır,
 *  kaydırma manifest'e yazılır. */
async function captureAsk(browser, fmt, data, out, manifest) {
  const { ctx, page, state } = await newPage(browser, fmt, data);
  await page.goto(`${SITE}/dashboard/ask?articleId=${data.hero.id}`, { waitUntil: "load" });
  await page.waitForSelector("form.chat-form input");
  await settle(page, 1200);
  const toBottom = () => page.evaluate(() => { window.scrollTo(0, document.documentElement.scrollHeight); return window.scrollY; });
  const shot = async (name) => { const scroll = await toBottom(); await jpg(page, path.join(out, `${name}.jpg`)); return scroll; };
  const input = page.locator("form.chat-form input");
  await input.evaluate((el) => { el.placeholder = ""; });
  await input.click();
  const scrolls = { blank: await shot("ask-blank") };
  await input.fill(data.question);
  scrolls.typed = await shot("ask-typed");
  const typed = await page.evaluate(() => window.__nx.ask());

  let release;
  state.askGate = { promise: new Promise((res) => { release = res; }) };
  await input.press("Enter");
  await settle(page, 700);
  scrolls.pending = await shot("ask-pending");
  const pending = await page.evaluate(() => window.__nx.ask());
  release();
  await page.waitForSelector(".chat-messages .card-sm >> nth=1");
  await settle(page, 900);
  scrolls.answer = await shot("ask-answer");
  const answer = await page.evaluate(() => window.__nx.ask());
  // Cevap balonu boş (metin/rozet/kaynak gizli) — Remotion cevabı satır satır açar.
  await page.evaluate(() => {
    const ans = [...document.querySelectorAll(".chat-messages .card-sm")][1];
    for (const el of ans.children) el.style.visibility = "hidden";
  });
  scrolls.answerBlank = await shot("ask-answer-blank");
  manifest.ask = { scrolls, typed, pending, answer };
  await ctx.close();
}

/** 7. sahne: semantik arama. Geçmişte bir eski arama var ki "son aramalar" satırı
 *  arama öncesi ve sonrası aynı yükseklikte kalsın (sonuç kartları hizalı üst üste biner). */
async function captureSearch(browser, fmt, data, out, manifest) {
  const { ctx, page } = await newPage(browser, fmt, data, { history: data.searchHistory });
  await page.goto(`${SITE}/dashboard/search`, { waitUntil: "load" });
  await page.waitForSelector("main input");
  await settle(page, 1200);
  const input = page.locator("main input").first();
  await input.evaluate((el) => { el.placeholder = ""; });
  await input.click();
  await jpg(page, path.join(out, "search-blank.jpg"));
  await input.fill(data.searchQuery);
  await jpg(page, path.join(out, "search-typed.jpg"));
  const typed = await page.evaluate(() => window.__nx.search());
  await input.press("Enter");
  await page.waitForSelector("main .card");
  await settle(page, 1200);
  await jpg(page, path.join(out, "search-results.jpg"));
  const results = await page.evaluate(() => window.__nx.search());
  // Sonuç kartları gizli hâl — Remotion kartları tek tek kaydırarak getirir.
  await page.evaluate(() => { for (const c of document.querySelectorAll("main .card")) c.style.visibility = "hidden"; });
  await jpg(page, path.join(out, "search-results-blank.jpg"));
  manifest.search = { scroll: await page.evaluate(() => window.scrollY), typed, results };
  await ctx.close();
}

/** 8. sahne: Hesabım (tam sayfa) + bülten tercihi adımları. */
async function captureAccount(browser, fmt, data, out, manifest) {
  const state = createMockState(data, { saved: [data.hero.id, 4, 7] });
  const { ctx, page } = await newPage(browser, fmt, data, { state });
  await page.goto(`${SITE}/account`, { waitUntil: "load" });
  await page.waitForSelector("#newsletter");
  await settle(page, 1800);
  const steps = [];
  const snap = async (name) => {
    const h = await page.evaluate(() => document.documentElement.scrollHeight);
    if (h > (page.viewportSize()?.height ?? 0)) await tallViewport(page, fmt, h);
    await jpg(page, path.join(out, `${name}.jpg`));
    steps.push({ name, layout: await page.evaluate(() => window.__nx.account()) });
  };
  await snap("account-0");
  const nl = page.locator("#newsletter");
  await nl.locator('button[type="button"]:not(.badge)').first().click(); // Günlük özet
  await settle(page, 250);
  await snap("account-freq");
  for (const [i, label] of data.newsletterTopics.entries()) {
    await nl.locator("button.badge", { hasText: new RegExp(`^${label}$`) }).first().click();
    await settle(page, 250);
    await snap(`account-${i + 1}`);
  }
  const kw = nl.locator('input[type="text"]');
  await kw.fill(data.newsletterKeyword);
  await snap("account-typed");
  await kw.press("Enter");
  await settle(page, 300);
  await snap("account-keyword");
  await nl.locator('button.btn-primary:not([type="button"])').click();
  await settle(page, 900);
  await snap("account-saved");
  manifest.account = { picks: data.newsletterTopics, steps };
  await ctx.close();
}

/** 9. sahne: gerçek bülten şablonu (digest.py) → görüntü. */
async function captureDigest(browser, fmt, data, out, manifest) {
  const tmp = path.join(out, "_digest");
  fs.mkdirSync(tmp, { recursive: true });
  const json = path.join(tmp, "articles.json");
  const html = path.join(tmp, "digest.html");
  fs.writeFileSync(json, JSON.stringify(data.digest), "utf8");
  execFileSync(PYTHON, [path.join(HERE, "digest.py"), data.lang, json, html], { cwd: REPO, stdio: "inherit" });
  const f = FORMATS[fmt];
  const ctx = await browser.newContext({ viewport: { width: f.emailWidth, height: 800 }, deviceScaleFactor: f.dpr });
  const page = await ctx.newPage();
  await page.goto(`file:///${html.replace(/\\/g, "/")}`, { waitUntil: "load" });
  const size = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight }));
  await jpg(page, path.join(out, "digest.jpg"), { fullPage: true });
  manifest.digest = { size, width: f.emailWidth, dpr: f.dpr };
  await ctx.close();
  fs.rmSync(tmp, { recursive: true, force: true });
}

/** Teşhis (yalnız açıkça istenince): ölçülen dikdörtgenleri sayfaya çizip uzun görünümle görüntü alır. */
async function captureDebug(browser, fmt, data, out) {
  const { ctx, page, ws } = await newPage(browser, fmt, data);
  await page.goto(`${SITE}/dashboard`, { waitUntil: "load" });
  await page.waitForSelector("main article.card");
  await settle(page, 1500);
  (await ws).send(JSON.stringify({ type: "article", data: data.live }));
  await settle(page, 1200);
  await page.setViewportSize({ width: FORMATS[fmt].viewport.width, height: 1600 });
  await settle(page, 400);
  const c = await page.evaluate(() => ({ coarse: matchMedia("(pointer: coarse)").matches, card: window.__nx.card(1) }));
  await page.evaluate((card) => {
    for (const r of [card.source, card.chips, card.footer, card.card]) {
      const d = document.createElement("div");
      Object.assign(d.style, { position: "absolute", left: `${r.x}px`, top: `${r.y}px`, width: `${r.w}px`, height: `${r.h}px`, outline: "3px solid magenta", zIndex: 99999, pointerEvents: "none" });
      document.body.appendChild(d);
    }
  }, c.card);
  await jpg(page, path.join(out, "debug-tall.jpg"));
  console.log(JSON.stringify({ coarse: c.coarse, source: c.card.source }));
  await ctx.close();
}

// ── giriş ───────────────────────────────────────────────────────────────────

const SCENES = { themes: captureThemes, feed: captureFeedAndCard, ask: captureAsk, search: captureSearch, account: captureAccount, digest: captureDigest, debug: captureDebug };
const ON_DEMAND = new Set(["debug"]);

async function main() {
  const [onlyLang, onlyFmt, ...onlyScenes] = process.argv.slice(2);
  const res = await fetch(SITE).catch(() => null);
  if (!res?.ok) {
    console.error(`Site ${SITE} yanıt vermiyor. Önce: cd frontend; npm run build; npx next start --port 3100`);
    process.exit(1);
  }
  const browser = await chromium.launch({ executablePath: findChrome() });
  for (const lang of onlyLang && onlyLang !== "all" ? [onlyLang] : ["TR", "EN"]) {
    for (const fmt of onlyFmt && onlyFmt !== "all" ? [onlyFmt] : Object.keys(FORMATS)) {
      const out = path.join(OUT_ROOT, `${lang}-${fmt}`);
      fs.mkdirSync(out, { recursive: true });
      const manifestPath = path.join(out, "manifest.json");
      const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, "utf8")) : {};
      manifest.viewport = FORMATS[fmt].viewport;
      manifest.dpr = FORMATS[fmt].dpr;
      const data = buildData(lang);
      for (const [name, fn] of Object.entries(SCENES)) {
        if (onlyScenes.length ? !onlyScenes.includes(name) : ON_DEMAND.has(name)) continue;
        const t0 = Date.now();
        await fn(browser, fmt, data, out, manifest);
        console.log(`${lang}-${fmt} ${name} ✓ (${((Date.now() - t0) / 1000).toFixed(1)} sn)`);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 1));
      }
    }
  }
  await browser.close();
}

main().catch((e) => { console.error(e); process.exit(1); });
