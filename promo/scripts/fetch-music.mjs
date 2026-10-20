// Arka plan müziğini indirir. Mixkit Stock Music Free License: videoda ticari kullanım
// serbest, atıf gerekmez; ham dosya YENİDEN DAĞITILAMAZ — bu yüzden mp3 repoya girmez
// (.gitignore), her makinede bu betikle indirilir.
// Parça: "Digital Clouds" — Alejandro Magaña (A. M.), https://mixkit.co/free-stock-music/tag/technology/
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const URL_ = "https://assets.mixkit.co/music/175/175.mp3";
const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public", "music", "digital-clouds.mp3");

if (fs.existsSync(OUT)) {
  console.log("zaten var:", OUT);
} else {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  const res = await fetch(URL_, { headers: { "User-Agent": "Mozilla/5.0" } });
  if (!res.ok) throw new Error(`indirme başarısız: ${res.status}`);
  fs.writeFileSync(OUT, Buffer.from(await res.arrayBuffer()));
  console.log("indirildi:", OUT);
}
