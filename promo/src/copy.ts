// Videodaki TÜM metin — dil başına bir blok (if/else dil dallanması yok, bkz. CLAUDE.md
// KODLAMA KURALLARI). Yeni dil = yeni blok + Root.tsx'teki LANGS listesine ekleme.

export type Lang = "TR" | "EN";

export interface Copy {
  hook: [string, string];
  hookHeadlines: string[];
  slogan: string;
  themes: { caption: string; tags: Record<string, string> };
  dive: { caption: string; live: string; market: string; trending: string; filters: string };
  card: {
    captionKnow: string; captionDeeper: string;
    source: string; topicSentiment: string; trust: string; chips: string; actions: string;
    related: string; sources: string; listen: string; saved: string; ask: string;
  };
  ask: { caption: string; sources: string; alert: string };
  search: { caption: string; score: string };
  account: { caption: string; sections: string[]; newsletter: string };
  mail: {
    caption: string; app: string; timeSkip: string; folders: string[]; searchPlaceholder: string; compose: string;
    others: { from: string; subject: string; time: string }[];
    from: string; subject: string; snippet: string; toast: string; to: string; now: string;
  };
  outro: { line: string; chips: string[]; url: string; cta: string };
}

export const COPY: Record<Lang, Copy> = {
  TR: {
    hook: ["Her gün yüzlerce haber.", "Hangisi gerçekten önemli?"],
    hookHeadlines: [
      "Merkez bankası faiz kararını açıkladı", "Ligde zirve yarışı kızıştı", "Katlanabilir telefonlar ucuzluyor",
      "Kuraklık uyarısı", "Kripto paralarda sert dalgalanma", "Yeni metro hattı", "Yerli elektrikli otomobil",
      "Yapay zekâ ile tarım", "Uzayda yeni uydu", "Borsa güne yükselişle başladı", "Akaryakıta indirim beklentisi",
      "Yeni nesil işlemci tanıtıldı", "Transfer döneminde sürpriz", "Sağlıkta yeni düzenleme", "Konser takvimi açıklandı",
      "Hava sıcaklıkları düşüyor", "Bilim insanlarından yeni keşif", "Döviz kurlarında geri çekilme",
    ],
    slogan: "Gürültüyü kes. Haberin özünü yakala.",
    themes: {
      caption: "Haberin, senin tarzında. 10 sinematik tema.",
      tags: { matrix: "Dijital Yağmur", godfather: "Sinematik Sepya", cyberpunk: "Neon Şehir", dune: "Çöl Fırtınası",
        starwars: "Hiperuzay", spiderman: "Örümcek Ağı", batman: "Gotham", wolfenstein: "Dizelpunk", night: "Gece Modu", day: "Gündüz Modu" },
    },
    dive: { caption: "17 kaynak. Canlı. Yapay zekâ ile analiz edilmiş.", live: "Yeni haber anında düşer", market: "Canlı piyasa şeridi",
      trending: "Gündemdeki konular", filters: "Duygu · konu · kaynak · kalite filtresi" },
    card: {
      captionKnow: "Okumadan önce bil: ton, güven, kaç kaynak doğruluyor.", captionDeeper: "Tek tıkla daha derine in.",
      source: "Kaynak · ne zaman", topicSentiment: "Konu + duygu analizi", trust: "Kaç kaynak doğruluyor · güven skoru",
      chips: "Kişi · kurum · yer etiketleri", actions: "Tek tıkla aksiyonlar",
      related: "İlgili haberler, ortak etiketleriyle", sources: "Aynı haberi veren diğer kaynaklar", listen: "Haberi sesli dinle",
      saved: "Kaydedildi → Hesabım", ask: "Bu habere soru sor",
    },
    ask: { caption: "Sor. Cevap, kaynağıyla gelsin.", sources: "Her iddia numaralı kaynağa bağlı", alert: "Konu gelişirse haber ver" },
    search: { caption: "Kelimeyi değil, anlamı ara.", score: "% anlam benzerliği" },
    account: { caption: "Her şey senin kontrolünde.", sections: ["Profil ve plan", "Kullanım ve kota", "Geliştirici API anahtarı", "Kaydedilenler", "Kişisel bülten"],
      newsletter: "Konunu seç, anahtar kelimeni ekle" },
    mail: {
      caption: "İlgilendiğin haberler, her sabah gelen kutunda.", app: "Posta", timeSkip: "Ertesi sabah",
      folders: ["Gelen Kutusu", "Yıldızlı", "Ertelenenler", "Gönderilmiş", "Taslaklar"], searchPlaceholder: "Postalarda ara", compose: "Yeni ileti",
      others: [
        { from: "Banka", subject: "Hesap özetiniz hazır", time: "Dün" },
        { from: "Kargo", subject: "Siparişiniz yola çıktı", time: "Dün" },
        { from: "Takvim", subject: "Hatırlatma: Proje toplantısı 10:30", time: "Pzt" },
        { from: "Kütüphane", subject: "Ödünç süreniz yaklaşıyor", time: "Pzt" },
      ],
      from: "NexStream", subject: "NexStream Günlük Özet", snippet: "Merkez bankası faiz kararını açıkladı · Yerli elektrikli otomobil…",
      toast: "Günlük özetin hazır", to: "alıcı: ben", now: "08:00",
    },
    outro: {
      line: "Hepsi tek yerde.",
      chips: ["⚡ Canlı akış", "🔔 Anlık bildirim", "📈 Piyasa şeridi", "🔥 Gündem", "🌍 Türkçe / English", "📱 Telefona kur", "🧩 Geliştirici API'si", "⇩ CSV / JSON dışa aktar"],
      url: "nexstreamnews.com", cta: "Ücretsiz başla →",
    },
  },
  EN: {
    hook: ["Hundreds of headlines every day.", "Which ones actually matter?"],
    hookHeadlines: [
      "Central bank announces rate decision", "Title race heats up", "Foldable phones get cheaper", "Drought warning",
      "Crypto markets swing sharply", "New metro line", "New electric car unveiled", "AI-powered farming", "New satellite in orbit",
      "Stocks open higher", "Fuel prices expected to drop", "Next-gen chip revealed", "Surprise in transfer window",
      "New health regulation", "Concert tour announced", "Temperatures dropping", "Scientists report new discovery", "Currencies pull back",
    ],
    slogan: "Cut the noise. Catch the story.",
    themes: {
      caption: "Your news, your look. 10 cinematic themes.",
      tags: { matrix: "Digital Rain", godfather: "Cinematic Sepia", cyberpunk: "Neon City", dune: "Desert Storm",
        starwars: "Hyperspace", spiderman: "Web Slinger", batman: "Gotham", wolfenstein: "Dieselpunk", night: "Night Mode", day: "Day Mode" },
    },
    dive: { caption: "17 sources. Live. Analyzed by AI.", live: "New stories drop in instantly", market: "Live market ticker",
      trending: "Trending topics", filters: "Filter by tone · topic · source · quality" },
    card: {
      captionKnow: "Know before you read: tone, trust, how many sources agree.", captionDeeper: "One tap to go deeper.",
      source: "Source · when", topicSentiment: "Topic + sentiment analysis", trust: "Sources that agree · trust score",
      chips: "People · organizations · places", actions: "One-tap actions",
      related: "Related stories, with shared entities", sources: "Other outlets covering the story", listen: "Listen to the story",
      saved: "Saved → My Account", ask: "Ask about this story",
    },
    ask: { caption: "Ask. Get answers with sources.", sources: "Every claim linked to a numbered source", alert: "Get notified when it develops" },
    search: { caption: "Search by meaning, not keywords.", score: "% semantic match" },
    account: { caption: "Everything under your control.", sections: ["Profile and plan", "Usage and quota", "Developer API key", "Saved stories", "Personal newsletter"],
      newsletter: "Pick your topics, add your keywords" },
    mail: {
      caption: "The news you care about, in your inbox every morning.", app: "Mail", timeSkip: "Next morning",
      folders: ["Inbox", "Starred", "Snoozed", "Sent", "Drafts"], searchPlaceholder: "Search mail", compose: "Compose",
      others: [
        { from: "Bank", subject: "Your statement is ready", time: "Yesterday" },
        { from: "Delivery", subject: "Your order is on its way", time: "Yesterday" },
        { from: "Calendar", subject: "Reminder: Project meeting 10:30", time: "Mon" },
        { from: "Library", subject: "Your loan is due soon", time: "Mon" },
      ],
      from: "NexStream", subject: "NexStream Daily Digest", snippet: "Central bank announces rate decision · New electric car model…",
      toast: "Your daily digest is ready", to: "to: me", now: "8:00 AM",
    },
    outro: {
      line: "All in one place.",
      chips: ["⚡ Live feed", "🔔 Instant alerts", "📈 Market ticker", "🔥 Trending", "🌍 English / Türkçe", "📱 Install on your phone", "🧩 Developer API", "⇩ CSV / JSON export"],
      url: "nexstreamnews.com", cta: "Start free →",
    },
  },
};
