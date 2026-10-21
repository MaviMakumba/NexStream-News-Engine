// Tüm çıktıları üretir: 4 ana video (TR/EN × yatay/dikey), README için ≤10 MB 720p
// sürümler ve kapak görselleri. Tek paket + tek tarayıcı.
// Kullanım: node scripts/render-all.mjs [filtre]   (örn. "TR-desktop" yalnız onu üretir)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, renderStill, selectComposition } from "@remotion/renderer";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "out");
const filter = process.argv[2] ?? "";

// Kapak karesi: logo + slogan tam görünürken (logo sahnesi, 6. vuruş civarı).
const POSTER_FRAME = 205;

const JOBS = [
  { id: "Promo-TR-desktop", file: "nexstream-tanitim-tr-1080p.mp4", poster: "nexstream-tanitim-tr.jpg" },
  { id: "Promo-EN-desktop", file: "nexstream-promo-en-1080p.mp4", poster: "nexstream-promo-en.jpg" },
  { id: "Promo-TR-mobile", file: "nexstream-tanitim-tr-dikey.mp4", poster: "nexstream-tanitim-tr-dikey.jpg" },
  { id: "Promo-EN-mobile", file: "nexstream-promo-en-vertical.mp4", poster: "nexstream-promo-en-vertical.jpg" },
  // README (GitHub ücretsiz yükleme sınırı 10 MB) — yatay, 720p
  { id: "Promo-TR-desktop", file: "readme-tr-720p.mp4", scale: 2 / 3, videoBitrate: "1150k" },
  { id: "Promo-EN-desktop", file: "readme-en-720p.mp4", scale: 2 / 3, videoBitrate: "1150k" },
];

fs.mkdirSync(OUT, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.join(ROOT, "src", "index.ts") });
const browser = await openBrowser("chrome", { browserExecutable: process.env.PW_CHROME ?? null });

for (const job of JOBS.filter((j) => !filter || j.id.includes(filter) || j.file.includes(filter))) {
  const composition = await selectComposition({ serveUrl, id: job.id, puppeteerInstance: browser });
  const output = path.join(OUT, job.file);
  const t0 = Date.now();
  let last = -1;
  await renderMedia({
    composition, serveUrl, codec: "h264", outputLocation: output, puppeteerInstance: browser,
    scale: job.scale ?? 1, x264Preset: "slow", pixelFormat: "yuv420p",
    ...(job.videoBitrate ? { videoBitrate: job.videoBitrate } : { crf: 20 }),
    audioCodec: "aac", audioBitrate: job.videoBitrate ? "128k" : "192k", concurrency: 4,
    onProgress: ({ progress }) => {
      const pct = Math.floor(progress * 10);
      if (pct !== last) { last = pct; process.stdout.write(`${job.file} %${pct * 10}\n`); }
    },
  });
  const mb = (fs.statSync(output).size / 1e6).toFixed(1);
  console.log(`✓ ${job.file} — ${mb} MB, ${((Date.now() - t0) / 60000).toFixed(1)} dk`);
  if (job.poster) {
    await renderStill({ composition, serveUrl, frame: POSTER_FRAME, output: path.join(OUT, job.poster), imageFormat: "jpeg", jpegQuality: 88, puppeteerInstance: browser });
  }
}
await browser.close({ silent: true });
