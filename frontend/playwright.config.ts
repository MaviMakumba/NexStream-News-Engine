import { defineConfig } from "@playwright/test";

// Mobil kullanÄ±labilirlik denetimi â€” bkz. e2e/mobile-audit.spec.ts.
// Backend'e ihtiyaÃ§ duymaz: API Ã§aÄŸrÄ±larÄ± testte taklit edilir (e2e/mock-api.ts).
// Ã–nce `npm run build`, sonra `npm run test:mobile`.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: true,
  workers: process.env.CI ? 2 : 4,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3100",
    // Chromium indirmesi bu ortamda güvenilmez (bkz. CLAUDE.md) — kuruluysa PW_CHROME ile göster.
    launchOptions: process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {},
  },
  webServer: {
    command: "npx next start --port 3100",
    url: "http://localhost:3100",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
