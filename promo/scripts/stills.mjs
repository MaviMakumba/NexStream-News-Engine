// Önizleme: seçili karelerden PNG üretir (tek paket + tek tarayıcı, hızlı).
// Kullanım: node scripts/stills.mjs <kompozisyon> <kare1,kare2,...> [çıktı-klasörü]
// Örn:      node scripts/stills.mjs Promo-TR-desktop 120,600,1700
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [id, framesArg, outArg] = process.argv.slice(2);
const frames = framesArg.split(",").map(Number);
const outDir = path.resolve(outArg ?? path.join(ROOT, "out", "stills"));
const serveUrl = await bundle({ entryPoint: path.join(ROOT, "src", "index.ts") });
const browser = await openBrowser("chrome", { browserExecutable: process.env.PW_CHROME ?? null });
const composition = await selectComposition({ serveUrl, id, puppeteerInstance: browser });
for (const frame of frames) {
  const output = path.join(outDir, `${id}-${String(frame).padStart(4, "0")}.png`);
  await renderStill({ composition, serveUrl, frame, output, puppeteerInstance: browser });
  console.log(output);
}
await browser.close({ silent: true });
