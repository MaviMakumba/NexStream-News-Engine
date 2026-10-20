// 9. Kişisel bülten: Gmail'i ANDIRAN ama markasız jenerik posta istemcisi. Zaman ileri
// sarılır, NexStream maili düşer, açılır — gövde sitenin GERÇEK bülten şablonu (digest.jpg).

import type React from "react";
import { AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { INTER } from "../fonts";
import { localBeat, SCENES } from "../timeline";
import { capture, usePromo } from "../components/context";
import { NIcon } from "../components/Logo";
import { Caption, Cursor, Sfx } from "../components/Overlay";

const BLUE = "#0b57d0";
const SENDER = "bildirim@nexstreamnews.com";

interface Beats { arrive: number; open: number }

function useBeats(): Beats {
  const b = (n: number) => localBeat(SCENES.mail.fromBeat, n);
  return { arrive: b(2), open: b(4.2) };
}

const Avatar: React.FC<{ letter: string; size: number; color: string }> = ({ letter, size, color }) => (
  <div style={{ width: size, height: size, borderRadius: "50%", background: color, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: size * 0.45, flexShrink: 0 }}>
    {letter}
  </div>
);

const AVATAR_COLORS = ["#5f6368", "#1e8e3e", "#e37400", "#9334e6"];

/** Ertesi sabaha atlama: koyu perde + saat. */
const TimeSkip: React.FC = () => {
  const frame = useCurrentFrame();
  const { copy, spec } = usePromo();
  const o = interpolate(frame, [0, 3, 20, 28], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const spin = interpolate(frame, [0, 20], [-200, 0], { extrapolateRight: "clamp" });
  const size = spec.hook.title * 1.4;
  return (
    <AbsoluteFill style={{ background: "rgba(10,10,16,.94)", opacity: o, alignItems: "center", justifyContent: "center", fontFamily: INTER, zIndex: 20 }}>
      <div style={{ position: "relative", width: size * 1.6, height: size * 1.6, borderRadius: "50%", border: "6px solid rgba(255,255,255,.85)" }}>
        <div style={{ position: "absolute", left: "50%", top: "50%", width: 6, height: size * 0.55, background: "#fff", transformOrigin: "50% 0", transform: `translateX(-50%) rotate(${180 + spin * 6}deg)` }} />
        <div style={{ position: "absolute", left: "50%", top: "50%", width: 6, height: size * 0.4, background: "#ff6b75", transformOrigin: "50% 0", transform: `translateX(-50%) rotate(${180 + spin * 0.5 + 60}deg)` }} />
      </div>
      <div style={{ marginTop: 34, color: "#fff", fontWeight: 800, fontSize: size * 0.5 }}>{copy.mail.now}</div>
      <div style={{ marginTop: 6, color: "rgba(255,255,255,.75)", fontWeight: 600, fontSize: size * 0.24 }}>{copy.mail.timeSkip}</div>
    </AbsoluteFill>
  );
};

const DesktopMail: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { copy, m, variant, lang } = usePromo();
  const B = useBeats();
  const rowIn = spring({ frame: frame - B.arrive, fps, config: { damping: 18 } });
  const toast = interpolate(frame, [B.arrive + 2, B.arrive + 10, B.open + 10, B.open + 18], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const opened = spring({ frame: frame - B.open, fps, config: { damping: 20 } });
  const imgW = 980;
  const imgH = imgW * (m.digest.size.h / m.digest.size.w);
  const scroll = interpolate(frame, [B.open + 14, durationInFrames], [0, Math.max(0, imgH - 640)], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ROW = 66;
  const unread = frame >= B.arrive;
  const curX = interpolate(frame, [B.open - 14, B.open - 2], [1500, 900], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const curY = interpolate(frame, [B.open - 14, B.open - 2], [760, 236], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "#f6f8fc", fontFamily: INTER, color: "#1f1f1f" }}>
      {/* üst çubuk */}
      <div style={{ height: 96, display: "flex", alignItems: "center", padding: "0 28px", gap: 22 }}>
        <div style={{ fontSize: 34, color: "#444" }}>☰</div>
        <div style={{ width: 52, height: 52, borderRadius: 14, background: "linear-gradient(135deg,#4f7cff,#7b5cff)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 30 }}>✉</div>
        <div style={{ fontSize: 30, fontWeight: 600, color: "#3c4043", width: 180 }}>{copy.mail.app}</div>
        <div style={{ flex: 1, maxWidth: 820, height: 60, borderRadius: 30, background: "#e9eef6", display: "flex", alignItems: "center", padding: "0 26px", color: "#5f6368", fontSize: 24, gap: 16 }}>
          <span>🔍</span>{copy.mail.searchPlaceholder}
        </div>
        <div style={{ flex: 1 }} />
        <Avatar letter={lang === "TR" ? "D" : "A"} size={50} color="#c31e2a" />
      </div>
      <div style={{ display: "flex", height: 1080 - 96 }}>
        {/* kenar çubuğu */}
        <div style={{ width: 300, padding: "6px 16px" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 14, padding: "20px 30px", borderRadius: 20, background: "#c2e7ff", fontSize: 23, fontWeight: 600, marginBottom: 18 }}>✎ {copy.mail.compose}</div>
          {copy.mail.folders.map((f, i) => (
            <div key={f} style={{ display: "flex", justifyContent: "space-between", padding: "14px 24px", borderRadius: 999, fontSize: 22, fontWeight: i === 0 ? 700 : 500, background: i === 0 ? "#d3e3fd" : "transparent" }}>
              <span>{f}</span>{i === 0 && unread && <span>1</span>}
            </div>
          ))}
        </div>
        {/* ana panel */}
        <div style={{ flex: 1, margin: "0 18px 18px 0", background: "#fff", borderRadius: 18, overflow: "hidden", position: "relative" }}>
          <div style={{ position: "absolute", inset: 0, transform: `translateX(${-opened * 30}%)`, opacity: 1 - opened }}>
            <div style={{ height: 64, borderBottom: "1px solid #eee", display: "flex", alignItems: "center", padding: "0 26px", color: "#5f6368", fontSize: 22, gap: 24 }}>☐ ⟳ ⋮</div>
            <div style={{ height: ROW * rowIn, overflow: "hidden", background: `rgba(255,236,179,${0.6 * (1 - Math.min(1, Math.max(0, (frame - B.arrive - 20) / 30)))})` }}>
              <MailRow from={copy.mail.from} subject={copy.mail.subject} snippet={copy.mail.snippet} time={copy.mail.now} unread icon />
            </div>
            {copy.mail.others.map((o) => <MailRow key={o.subject} from={o.from} subject={o.subject} snippet="" time={o.time} />)}
          </div>
          {opened > 0.01 && (
            <div style={{ position: "absolute", inset: 0, padding: "30px 46px", opacity: opened, transform: `translateX(${(1 - opened) * 20}%)` }}>
              <div style={{ fontSize: 34, fontWeight: 500, marginBottom: 22 }}>{copy.mail.subject} <span style={{ fontSize: 18, background: "#e8eaed", padding: "4px 10px", borderRadius: 6, verticalAlign: "middle" }}>{copy.mail.folders[0]}</span></div>
              <div style={{ display: "flex", alignItems: "center", gap: 18, marginBottom: 20 }}>
                <NIcon size={56} glow={0.2} />
                <div style={{ fontSize: 21 }}>
                  <div><b>{copy.mail.from}</b> <span style={{ color: "#5f6368" }}>&lt;{SENDER}&gt;</span></div>
                  <div style={{ color: "#5f6368" }}>{copy.mail.to}</div>
                </div>
                <div style={{ flex: 1 }} />
                <div style={{ color: "#5f6368", fontSize: 20 }}>{copy.mail.now}</div>
              </div>
              <div style={{ height: 660, overflow: "hidden", borderRadius: 12 }}>
                <Img src={capture(variant, "digest.jpg")} style={{ width: imgW, transform: `translateY(${-scroll}px)` }} />
              </div>
            </div>
          )}
        </div>
      </div>
      {/* bildirim */}
      <div style={{
        position: "absolute", left: 40, bottom: 40 + 160 * (1 - toast), opacity: toast, display: "flex", alignItems: "center", gap: 18,
        background: "#202124", color: "#fff", padding: "18px 26px", borderRadius: 16, fontSize: 23, boxShadow: "0 12px 30px rgba(0,0,0,.35)",
      }}>
        <NIcon size={44} glow={0.3} /> <b>{copy.mail.from}</b> · {copy.mail.toast}
      </div>
      <Cursor x={curX} y={curY} clicks={[B.open]} opacity={interpolate(frame, [B.open - 14, B.open - 8, B.open + 10, B.open + 18], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
    </AbsoluteFill>
  );
};

const MailRow: React.FC<{ from: string; subject: string; snippet: string; time: string; unread?: boolean; icon?: boolean }> = ({ from, subject, snippet, time, unread, icon }) => (
  <div style={{ height: 66, display: "flex", alignItems: "center", padding: "0 26px", gap: 22, borderBottom: "1px solid #f1f3f4", fontSize: 22, fontWeight: unread ? 700 : 400 }}>
    <span style={{ color: "#bbb" }}>☐</span>
    <span style={{ color: unread ? "#f4b400" : "#ccc" }}>★</span>
    <span style={{ width: 230, display: "flex", alignItems: "center", gap: 12 }}>{icon && <NIcon size={30} glow={0.2} />}{from}</span>
    <span style={{ flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
      {subject}{snippet && <span style={{ fontWeight: 400, color: "#5f6368" }}> — {snippet}</span>}
    </span>
    <span style={{ fontSize: 19, color: unread ? "#1f1f1f" : "#5f6368" }}>{time}</span>
  </div>
);

const MobileMail: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { copy, m, variant } = usePromo();
  const B = useBeats();
  const rowIn = spring({ frame: frame - B.arrive, fps, config: { damping: 18 } });
  const banner = interpolate(frame, [B.arrive + 2, B.arrive + 10, B.open - 6, B.open], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const opened = spring({ frame: frame - B.open, fps, config: { damping: 20 } });
  const imgW = 1032;
  const imgH = imgW * (m.digest.size.h / m.digest.size.w);
  const scroll = interpolate(frame, [B.open + 14, durationInFrames], [0, Math.max(0, imgH - 1150)], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const ROW = 168;
  return (
    <AbsoluteFill style={{ background: "#fff", fontFamily: INTER, color: "#1f1f1f" }}>
      <div style={{ height: 80, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 48px", fontSize: 30, fontWeight: 700 }}>
        <span>{copy.mail.now}</span><span>▮▮▮ ◔</span>
      </div>
      <div style={{ position: "absolute", top: 80, left: 0, right: 0, bottom: 0, transform: `translateX(${-opened * 30}%)`, opacity: 1 - opened }}>
        <div style={{ margin: "380px 36px 20px", height: 96, borderRadius: 48, background: "#eef2f8", display: "flex", alignItems: "center", padding: "0 36px", color: "#5f6368", fontSize: 32, gap: 20 }}>☰ <span style={{ flex: 1 }}>{copy.mail.searchPlaceholder}</span></div>
        <div style={{ padding: "16px 48px", fontSize: 28, color: "#5f6368", fontWeight: 600 }}>{copy.mail.folders[0]}</div>
        <div style={{ height: ROW * rowIn, overflow: "hidden" }}>
          <MobileRow from={copy.mail.from} subject={copy.mail.subject} snippet={copy.mail.snippet} time={copy.mail.now} unread />
        </div>
        {copy.mail.others.map((o, i) => <MobileRow key={o.subject} from={o.from} subject={o.subject} snippet="" time={o.time} color={AVATAR_COLORS[i]} />)}
      </div>
      {opened > 0.01 && (
        <div style={{ position: "absolute", top: 80, left: 0, right: 0, bottom: 0, opacity: opened, transform: `translateX(${(1 - opened) * 20}%)`, padding: "380px 24px 0" }}>
          <div style={{ fontSize: 44, fontWeight: 600, margin: "0 24px 28px" }}>{copy.mail.subject}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 22, margin: "0 24px 26px" }}>
            <NIcon size={84} glow={0.2} />
            <div style={{ fontSize: 30 }}><b>{copy.mail.from}</b><div style={{ color: "#5f6368", fontSize: 26 }}>{copy.mail.to} · {copy.mail.now}</div></div>
          </div>
          <div style={{ height: 1150, overflow: "hidden", borderRadius: 18 }}>
            <Img src={capture(variant, "digest.jpg")} style={{ width: imgW, transform: `translateY(${-scroll}px)` }} />
          </div>
        </div>
      )}
      <div style={{
        position: "absolute", left: 30, right: 30, top: 100 - 260 * (1 - banner), opacity: banner, display: "flex", alignItems: "center", gap: 24,
        background: "rgba(245,245,247,.97)", padding: "28px 30px", borderRadius: 40, boxShadow: "0 16px 40px rgba(0,0,0,.25)", fontSize: 30,
      }}>
        <NIcon size={84} glow={0.2} />
        <div><b>{copy.mail.from}</b><div style={{ color: "#3c4043" }}>{copy.mail.toast}</div></div>
      </div>
      <Cursor x={540} y={80 + 380 + 96 + 20 + 70 + ROW / 2} clicks={[B.open]} opacity={interpolate(frame, [B.open - 10, B.open - 4, B.open + 8, B.open + 14], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
    </AbsoluteFill>
  );
};

const MobileRow: React.FC<{ from: string; subject: string; snippet: string; time: string; unread?: boolean; color?: string }> = ({ from, subject, snippet, time, unread, color = "#5f6368" }) => (
  <div style={{ height: 168, display: "flex", alignItems: "center", padding: "0 44px", gap: 28, background: unread ? "#fff8e1" : "#fff" }}>
    {unread ? <NIcon size={92} glow={0.2} /> : <Avatar letter={from[0]} size={92} color={color} />}
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 32, fontWeight: unread ? 800 : 500 }}><span>{from}</span><span style={{ fontSize: 26, fontWeight: 500, color: "#5f6368" }}>{time}</span></div>
      <div style={{ fontSize: 30, fontWeight: unread ? 700 : 400, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{subject}</div>
      {snippet && <div style={{ fontSize: 27, color: "#5f6368", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{snippet}</div>}
    </div>
  </div>
);

const LAYOUTS = { desktop: DesktopMail, mobile: MobileMail };

export const Mail: React.FC = () => {
  const { fmt, copy } = usePromo();
  const { durationInFrames } = useVideoConfig();
  const B = useBeats();
  const View = LAYOUTS[fmt];
  return (
    <AbsoluteFill>
      <View />
      <TimeSkip />
      <Caption text={copy.mail.caption} from={B.arrive - 4} to={durationInFrames - 2} />
      <Sfx at={0} name="whoosh" volume={0.5} />
      <Sfx at={B.arrive + 2} name="notify" volume={0.7} />
      <Sfx at={B.open} name="click" volume={0.6} />
      <Sfx at={B.open + 2} name="swoosh" volume={0.3} />
    </AbsoluteFill>
  );
};
