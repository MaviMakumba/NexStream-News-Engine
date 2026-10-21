"""Tanıtım videosunun ses efektlerini sentezler (lisans derdi yok, repoya girer).

Kullanım: venv/Scripts/python.exe promo/scripts/make_sfx.py
Çıktı:    promo/public/sfx/*.wav (44.1 kHz, 16-bit, mono). Sabit tohum → her çalıştırmada aynı dosya.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parents[1] / "public" / "sfx"
rng = np.random.default_rng(7)


def t_axis(sec: float) -> np.ndarray:
    return np.arange(int(sec * SR)) / SR


def lowpass(x: np.ndarray, cutoff: np.ndarray | float) -> np.ndarray:
    """Tek kutuplu alçak geçiren; cutoff örnek başına değişebilir (süpürme için)."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1.0 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, (xi, ai) in enumerate(zip(x, a)):
        acc += ai * (xi - acc)
        y[i] = acc
    return y


def bandpass(x: np.ndarray, center: np.ndarray | float, width: float = 0.6) -> np.ndarray:
    c = np.asarray(center, dtype=float)
    return lowpass(x, c * (1 + width)) - lowpass(x, c * (1 - width))


def env(n: int, attack: float, release: float, peak_at: float | None = None) -> np.ndarray:
    t = np.linspace(0, 1, n)
    p = peak_at if peak_at is not None else attack
    up = np.clip(t / max(p, 1e-6), 0, 1) ** 2
    down = np.clip((1 - t) / max(1 - p, 1e-6), 0, 1) ** (1 / max(release, 1e-6))
    return up * down


def norm(x: np.ndarray, peak: float) -> np.ndarray:
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def write(name: str, x: np.ndarray) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def whoosh(sec: float, f0: float, f1: float, peak_at: float, gain: float) -> np.ndarray:
    n = int(sec * SR)
    sweep = np.geomspace(f0, f1, n)
    x = bandpass(rng.standard_normal(n), sweep, 0.7)
    return norm(x * env(n, peak_at, 1.6, peak_at), gain)


def tone(sec: float, freqs: list[float], decays: list[float], amps: list[float]) -> np.ndarray:
    t = t_axis(sec)
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, d, a in zip(freqs, decays, amps))
    attack = np.clip(t / 0.004, 0, 1)
    return x * attack


def main() -> None:
    write("whoosh.wav", whoosh(0.7, 300, 4500, 0.55, 0.55))
    write("swoosh.wav", whoosh(0.38, 900, 6000, 0.45, 0.32))

    n = int(0.06 * SR)
    click = bandpass(rng.standard_normal(n), 3500, 0.5) * np.exp(-np.arange(n) / (0.006 * SR))
    click += tone(0.06, [2200], [0.008], [0.6])
    write("click.wav", norm(click, 0.5))

    for i, f in enumerate([1900, 2300, 2650]):
        m = int(0.035 * SR)
        key = bandpass(rng.standard_normal(m), f, 0.5) * np.exp(-np.arange(m) / (0.004 * SR))
        write(f"key{i + 1}.wav", norm(key, 0.22))

    t = t_axis(0.14)
    pop = np.sin(2 * np.pi * np.cumsum(np.geomspace(1100, 420, len(t))) / SR) * np.exp(-t / 0.035)
    write("pop.wav", norm(pop * np.clip(t / 0.002, 0, 1), 0.45))

    m = int(0.05 * SR)
    flick = bandpass(rng.standard_normal(m), np.geomspace(6000, 2500, m), 0.6) * np.exp(-np.arange(m) / (0.008 * SR))
    write("flick.wav", norm(flick, 0.3))

    write("ding.wav", norm(tone(1.4, [1318.5, 3637, 7120], [0.45, 0.18, 0.07], [1, 0.35, 0.12]), 0.42))
    chime = np.concatenate([tone(0.16, [1318.5, 2637], [0.12, 0.05], [1, 0.25]), tone(0.9, [1975.5, 3951], [0.3, 0.1], [1, 0.25])])
    write("notify.wav", norm(chime, 0.45))

    sec = 3.8
    n = int(sec * SR)
    tt = t_axis(sec)
    rise = (tt / sec) ** 2.2
    noise = bandpass(rng.standard_normal(n), np.geomspace(250, 5000, n), 0.5)
    sweep_tone = np.sin(2 * np.pi * np.cumsum(np.geomspace(180, 1400, n)) / SR) * 0.35
    write("riser.wav", norm((noise + sweep_tone) * rise, 0.5))

    tt = t_axis(1.6)
    boom = np.sin(2 * np.pi * np.cumsum(np.geomspace(95, 42, len(tt))) / SR) * np.exp(-tt / 0.45)
    hit = lowpass(rng.standard_normal(len(tt)), 900) * np.exp(-tt / 0.06) * 2.5
    write("impact.wav", norm((boom + hit) * np.clip(tt / 0.003, 0, 1), 0.7))

    print("sfx:", ", ".join(sorted(p.name for p in OUT.glob("*.wav"))))


if __name__ == "__main__":
    main()
