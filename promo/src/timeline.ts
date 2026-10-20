// Videonun tek zaman kaynağı. Tüm sahne sınırları müziğin vuruş ızgarasına oturur:
// "Digital Clouds" 129.00 BPM, vuruş 0 = parçanın 0,080. sn'si (analiz: scripts/README).
// Parçanın 64. vuruşundaki (29,847 sn) "swell" videonun 4,0. saniyesine (DROP) denk gelir.

export const FPS = 30;
export const BEAT = 60 / 129; // sn
export const DROP = 4.0; // sn — logonun belirdiği an

/** n. vuruşun (DROP'tan itibaren) video saniyesi. */
export const beatSec = (n: number) => DROP + n * BEAT;
/** n. vuruşun video karesi. */
export const beatFrame = (n: number) => Math.round(beatSec(n) * FPS);
/** Sahne içinde, sahne başından itibaren `n` vuruş sonrasının yerel karesi. */
export const localBeat = (sceneStartBeat: number, n: number) => beatFrame(sceneStartBeat + n) - beatFrame(sceneStartBeat);

export const DURATION_SEC = 57;
export const DURATION = DURATION_SEC * FPS;

// Sahneler vuruş cinsinden (DROP = 0). Kanca DROP'tan önceki 4 saniyedir.
export const SCENES = {
  hook: { from: 0, to: beatFrame(0) },
  logo: { fromBeat: 0, toBeat: 8 },
  themes: { fromBeat: 8, toBeat: 18 },
  dive: { fromBeat: 18, toBeat: 32 }, // 32 = müzikte yeni cümle → ana sahne
  card: { fromBeat: 32, toBeat: 56 },
  ask: { fromBeat: 56, toBeat: 68 },
  search: { fromBeat: 68, toBeat: 78 },
  account: { fromBeat: 78, toBeat: 92 },
  mail: { fromBeat: 92, toBeat: 104 },
  outro: { fromBeat: 104, toBeat: null }, // video sonuna kadar
} as const;

export const FINAL_HIT_BEAT = 109; // parçanın kendi son vuruşu (95,43 sn) → kapanış logosu

// Müzik kurgusu: parça DROP'a hizalı başlar, 160. vuruşta (74,50 sn) kendi son
// cümlesine (192. vuruş, 89,38 sn) atlar — iki nokta da 32 vuruşluk cümle başı.
const TRACK_PHASE = 0.08;
const trackBeat = (k: number) => TRACK_PHASE + k * BEAT;
export const MUSIC = {
  src: "music/digital-clouds.mp3",
  partA: { videoFrom: 0, trackFromSec: trackBeat(64) - DROP, videoTo: beatFrame(96) },
  partB: { videoFrom: beatFrame(96), trackFromSec: trackBeat(192) },
  crossfadeFrames: 6,
};

export type SceneName = keyof typeof SCENES;

export function sceneRange(name: SceneName): { from: number; duration: number } {
  if (name === "hook") return { from: 0, duration: SCENES.hook.to };
  const s = SCENES[name];
  const from = beatFrame(s.fromBeat);
  const to = s.toBeat === null ? DURATION : beatFrame(s.toBeat);
  return { from, duration: to - from };
}
