// Tanıtım videosu için KURGUSAL veri — gerçek kaynak adı/başlık/kişi YOK (telif + itibar
// riski, bkz. docs/superpowers/specs/2026-10-21-tanitim-videosu-design.md). Dil başına bir
// blok; yeni dil = yeni blok, capture.mjs'e dokunulmaz.

const ARTICLES = {
  TR: [
    { title: "Merkez bankası faiz kararını açıkladı: piyasalar güne yükselişle başladı", topic: "Economy", sentiment: "Positive", orgs: ["Merkez Bankası", "Borsa İstanbul"], locs: ["Ankara"], corroboration: 5, trust: 91,
      summary: "Kurulun beklentilere paralel kararının ardından hisse senetleri yükselirken döviz kurlarında sınırlı bir geri çekilme görüldü." },
    { title: "Yerli elektrikli otomobilin yeni modeli tanıtıldı, ön siparişler başladı", topic: "Technology", sentiment: "Positive", orgs: ["Elektrikli Araç"], locs: ["Bursa"], corroboration: 3, trust: 84,
      summary: "Yeni model daha uzun menzil ve hızlı şarj desteğiyle geliyor; teslimatların ilkbaharda başlaması planlanıyor." },
    { title: "Ligde zirve yarışı kızıştı: derbide kazanan çıkmadı", topic: "Sports", sentiment: "Neutral", orgs: ["Süper Lig"], locs: ["İstanbul"], corroboration: 4, trust: 79,
      summary: "Kritik maçta iki takım da gol bulamadı; zirvedeki puan farkı değişmedi." },
    { title: "Yapay zekâ destekli tarım projesi ilk hasadını verdi", topic: "Technology", sentiment: "Positive", orgs: ["Yapay Zekâ"], locs: ["Konya"], corroboration: 2, trust: 76,
      summary: "Sensör ve yapay zekâ ile sulanan pilot tarlalarda su tüketimi üçte bir azaldı." },
    { title: "Kuraklık uyarısı: barajlarda doluluk yüzde 40'ın altına indi", topic: "Environment", sentiment: "Negative", orgs: ["DSİ"], locs: ["İzmir"], corroboration: 3, trust: 88,
      summary: "Uzmanlar tasarruf çağrısı yaparken bazı ilçelerde planlı su kesintileri gündemde." },
    { title: "Katlanabilir telefon pazarı büyüyor, fiyatlar düşüşte", topic: "Technology", sentiment: "Neutral", orgs: [], locs: ["Seul"], corroboration: 2, trust: 72,
      summary: "Üreticilerin rekabeti katlanabilir modellerde fiyatları ilk kez orta segmente indirdi." },
    { title: "Şehrin yeni metro hattı için ilk sefer tarihi belli oldu", topic: "Politics", sentiment: "Positive", orgs: ["Metro"], locs: ["İstanbul"], corroboration: 3, trust: 81,
      summary: "Hattın tamamlanmasıyla iki ilçe arasındaki yolculuk süresi 15 dakikaya inecek." },
    { title: "Kripto paralarda hareketli gün: piyasa değeri sert dalgalandı", topic: "Crypto", sentiment: "Negative", orgs: ["Bitcoin"], locs: [], corroboration: 2, trust: 69,
      summary: "Yatırımcıların düzenleme haberlerine tepkisi gün içinde sert fiyat hareketlerine yol açtı." },
  ],
  EN: [
    { title: "Central bank announces rate decision as markets open higher", topic: "Economy", sentiment: "Positive", orgs: ["Central Bank", "Stock Exchange"], locs: ["Capital City"], corroboration: 5, trust: 91,
      summary: "Shares rallied after the board's in-line decision, while currencies saw a modest pullback." },
    { title: "New electric car model unveiled as pre-orders open", topic: "Technology", sentiment: "Positive", orgs: ["Electric Cars"], locs: ["Detroit"], corroboration: 3, trust: 84,
      summary: "The new model brings longer range and fast charging; deliveries are planned for spring." },
    { title: "Title race heats up as the derby ends goalless", topic: "Sports", sentiment: "Neutral", orgs: ["League"], locs: ["Manchester"], corroboration: 4, trust: 79,
      summary: "Neither side found the net in the crucial match, leaving the gap at the top unchanged." },
    { title: "AI-powered farming project delivers its first harvest", topic: "Technology", sentiment: "Positive", orgs: ["AI"], locs: ["Iowa"], corroboration: 2, trust: 76,
      summary: "Pilot fields irrigated with sensors and AI cut water use by a third." },
    { title: "Drought warning: reservoir levels fall below 40 percent", topic: "Environment", sentiment: "Negative", orgs: ["Water Agency"], locs: ["California"], corroboration: 3, trust: 88,
      summary: "Experts urge conservation as planned water cuts are discussed in several districts." },
    { title: "Foldable phone market grows as prices fall", topic: "Technology", sentiment: "Neutral", orgs: [], locs: ["Seoul"], corroboration: 2, trust: 72,
      summary: "Competition between makers has pushed foldable prices into the mid-range for the first time." },
    { title: "City's new metro line gets an opening date", topic: "Politics", sentiment: "Positive", orgs: ["Metro"], locs: ["Toronto"], corroboration: 3, trust: 81,
      summary: "Once complete, the line will cut the trip between two districts to 15 minutes." },
    { title: "Crypto markets swing sharply in a volatile session", topic: "Crypto", sentiment: "Negative", orgs: ["Bitcoin"], locs: [], corroboration: 2, trust: 69,
      summary: "Investor reaction to regulation news drove sharp price moves throughout the day." },
  ],
};

const SOURCE_PREFIX = { TR: "Kaynak", EN: "Source" };
const LETTERS = ["A", "B", "C", "D", "E", "F"];

const STRINGS = {
  TR: {
    user: { name: "Deniz", email: "deniz@example.com" },
    live: { title: "Uzay ajansı yeni nesil iletişim uydusunu başarıyla fırlattı", topic: "Science", sentiment: "Positive",
            summary: "Uydu, kırsal bölgelere yüksek hızlı internet ulaştırmak için tasarlandı." },
    trending: ["Merkez Bankası", "Süper Lig", "Yapay Zekâ", "Elektrikli Araç", "Kuraklık", "Metro"],
    related: ["Döviz kurlarında karar sonrası sınırlı geri çekilme", "Ekonomistler yılın kalanı için faiz patikasını değerlendirdi"],
    question: "Faiz kararı piyasaları nasıl etkiledi?",
    answer: "Faiz kararının ardından borsa güne yükselişle başladı [1]; döviz kurlarında ise sınırlı bir geri çekilme görüldü [2]. Ekonomistler kararın beklentilere paralel olduğunu ve yılın kalanında temkinli bir patika izlenebileceğini değerlendiriyor [3].",
    searchQuery: "yeşil enerji ve ulaşım",
    searchHistory: "yapay zekâ tarım",
    newsletterTopics: ["Ekonomi", "Teknoloji", "Spor"],
    newsletterKeyword: "elektrikli araç",
  },
  EN: {
    user: { name: "Alex", email: "alex@example.com" },
    live: { title: "Space agency successfully launches next-gen communications satellite", topic: "Science", sentiment: "Positive",
            summary: "The satellite is designed to bring high-speed internet to rural areas." },
    trending: ["Central Bank", "Title Race", "AI", "Electric Cars", "Drought", "Metro"],
    related: ["Currencies see modest pullback after the decision", "Economists weigh the rate path for the rest of the year"],
    question: "How did the rate decision affect markets?",
    answer: "After the rate decision, stocks opened the day higher [1], while currencies saw a modest pullback [2]. Economists say the move was in line with expectations and expect a cautious path for the rest of the year [3].",
    searchQuery: "green energy and transport",
    searchHistory: "ai farming",
    newsletterTopics: ["Economy", "Technology", "Sports"],
    newsletterKeyword: "electric cars",
  },
};

const MIN = 60_000;

/** Bir dilin tüm taklit verisi. `now` sayfanın (Playwright clock'unun) zamanı. */
export function buildData(lang, now = Date.now()) {
  const s = STRINGS[lang];
  const source = (i) => `${SOURCE_PREFIX[lang]} ${LETTERS[i % LETTERS.length]}`;
  const article = (a, i) => ({
    id: i + 1, title: a.title, source: source(i), url: `https://example.com/news/${i + 1}`, content: "",
    summary: a.summary, sentiment_label: a.sentiment, sentiment_score: 0.6, topic: a.topic,
    entities: { persons: [], organizations: a.orgs, locations: a.locs },
    quality_score: 0.8, credibility_score: 0.8, corroboration_count: a.corroboration, trust_score: a.trust,
    trust_breakdown: { quality: 30, credibility: 35, corroboration: a.trust - 65 },
    created_at: new Date(now - (i * 7 + 4) * MIN).toISOString(),
    published_at: new Date(now - (i * 7 + 4) * MIN).toISOString(),
  });
  const articles = ARTICLES[lang].map(article);
  const hero = articles[0];
  const sources = LETTERS.map((_, i) => source(i));

  return {
    lang,
    user: {
      id: 7, email: s.user.email, name: s.user.name, tier: "pro", role: "user", is_admin: false, is_moderator: false,
      is_owner: false, effective_tier: "pro", email_verified: true, created_at: "2026-08-01T00:00:00Z",
    },
    articles,
    hero,
    sources,
    live: {
      id: 100, title: s.live.title, source: source(4), url: "https://example.com/news/100", summary: s.live.summary,
      sentiment_label: s.live.sentiment, topic: s.live.topic, created_at: new Date(now).toISOString(),
    },
    trending: { hours: 6, entities: s.trending.map((name, i) => ({ name, count: 14 - i * 2, type: "organization", example_titles: [articles[i].title] })) },
    related: { article_id: hero.id, related: s.related.map((title, i) => ({ id: 30 + i, title, source: source(2 + i * 2), url: "https://example.com/r", common_entities: i ? hero.entities.organizations.concat(hero.entities.locations) : hero.entities.organizations.slice(0, 1), overlap_score: 0.6 - i / 10 })) },
    storySources: { article_id: hero.id, sources: [1, 2, 3, 5].map((k, i) => ({ id: 40 + i, title: hero.title, source: source(k), url: "https://example.com/s", score: 0.9, trust_score: 80 })) },
    // anlamsal arama: sorgudaki kelimeler başlıklarda GEÇMEZ, anlamı eşleşir
    search: [1, 6, 3, 4].map((k, i) => ({ ...articles[k], score: 0.91 - i * 0.04 })),
    ask: {
      answer: s.answer, coverage: "full", corroboration_level: "multi_source", suggest_alert: true,
      sources: [
        { index: 1, title: hero.title, source: hero.source, url: hero.url },
        { index: 2, title: s.related[0], source: source(2), url: "https://example.com/r" },
        { index: 3, title: s.related[1], source: source(4), url: "https://example.com/r" },
      ],
    },
    usage: { tier: "pro", daily_limit: 2000, used_today: 128, remaining_today: 1872, days: 7, total_requests: 846, has_api_key: true,
      by_endpoint: [
        { user_id: 7, endpoint: "/api/v1/news/search", count: 312, avg_ms: 140 },
        { user_id: 7, endpoint: "/api/v1/news/ask", count: 41, avg_ms: 2100 },
        { user_id: 7, endpoint: "/api/v1/news", count: 493, avg_ms: 60 },
      ] },
    market: { bist100: { value: 10482.5, change_pct: 1.24 }, usd_try: { value: 41.87, change_pct: -0.31 }, eur_try: { value: 48.6, change_pct: 0.12 },
      gold_gram_try: { value: 4385, change_pct: 0.54 }, as_of: new Date(now).toISOString(), stale: false },
    question: s.question,
    searchQuery: s.searchQuery,
    searchHistory: s.searchHistory,
    newsletterTopics: s.newsletterTopics,
    newsletterKeyword: s.newsletterKeyword,
    // bülten maili: seçilen konulara uyan haberler
    digest: [0, 1, 2, 5].map((k) => articles[k]),
  };
}
