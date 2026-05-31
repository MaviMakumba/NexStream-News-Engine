import type { Lang } from "./settings-context";

export const TOPIC_LABELS: Record<string, Record<string, string>> = {
  TR: {
    "": "Tüm Konular",
    Technology: "Teknoloji", Sports: "Spor", Economy: "Ekonomi",
    Politics: "Siyaset", Health: "Sağlık", Culture: "Kültür",
    World: "Dünya", Other: "Diğer",
  },
  EN: {
    "": "All Topics",
    Technology: "Technology", Sports: "Sports", Economy: "Economy",
    Politics: "Politics", Health: "Health", Culture: "Culture",
    World: "World", Other: "Other",
  },
};

export const SENTIMENT_LABELS: Record<string, Record<string, string>> = {
  TR: { "": "Tüm Duygular", Positive: "Pozitif", Negative: "Negatif", Neutral: "Nötr" },
  EN: { "": "All Sentiments", Positive: "Positive", Negative: "Negative", Neutral: "Neutral" },
};

export const UI: Record<Lang, Record<string, string>> = {
  TR: {
    dashboard: "Haberler", search: "Arama", admin: "Yönetim", account: "Hesabım",
    login: "Giriş Yap", register: "Kayıt Ol", logout: "Çıkış",
    trending: "Gündem", latestNews: "Son Haberler",
    allSources: "Tüm Kaynaklar", allQualities: "Tüm Kaliteler",
    qualityMed: "Orta+ (≥0.4)", qualityHigh: "Yüksek (≥0.6)",
    loadMore: "Daha fazla", loading: "Yükleniyor…",
    noTrending: "Gündem verisi yok",
    related: "İlgili haberler", hideRelated: "Gizle",
    loadingRelated: "Yükleniyor…", noRelated: "İlgili haber bulunamadı.",
    goToArticle: "Habere git →",
    searchPlaceholder: "bitcoin, deprem, yapay zeka…",
    searchBtn: "Ara", searchHistory: "Son aramalar",
    noResults: "için sonuç bulunamadı",
    semanticSearch: "Semantik Arama",
    semanticDesc: "Kelime tam eşleşmese de anlamsal olarak yakın haberler bulunur.",
    matchRate: "eşleşme",
    settings: "Ayarlar", theme: "Tema", language: "Dil",
    loginTitle: "Tekrar Hoş Geldiniz", loginSub: "Hesabınıza giriş yapın",
    registerTitle: "Ücretsiz Başlayın", registerSub: "Dakikalar içinde hesap oluşturun",
    emailLabel: "E-posta", passwordLabel: "Şifre", nameLabel: "İsim",
    loginBtn: "Giriş Yap", registerBtn: "Kayıt Ol — Ücretsiz",
    haveAccount: "Zaten hesabınız var mı?", noAccount: "Hesabınız yok mu?",
    signIn: "Giriş yapın", signUp: "Kayıt olun",
    loading2: "Lütfen bekleyin…",
  },
  EN: {
    dashboard: "News", search: "Search", admin: "Admin", account: "Account",
    login: "Sign In", register: "Register", logout: "Log Out",
    trending: "Trending", latestNews: "Latest News",
    allSources: "All Sources", allQualities: "All Qualities",
    qualityMed: "Medium+ (≥0.4)", qualityHigh: "High (≥0.6)",
    loadMore: "Load more", loading: "Loading…",
    noTrending: "No trending data",
    related: "Related articles", hideRelated: "Hide",
    loadingRelated: "Loading…", noRelated: "No related articles found.",
    goToArticle: "Read article →",
    searchPlaceholder: "bitcoin, earthquake, AI…",
    searchBtn: "Search", searchHistory: "Recent searches",
    noResults: "no results for",
    semanticSearch: "Semantic Search",
    semanticDesc: "Finds semantically similar articles even without exact keyword matches.",
    matchRate: "match",
    settings: "Settings", theme: "Theme", language: "Language",
    loginTitle: "Welcome Back", loginSub: "Sign in to your account",
    registerTitle: "Start for Free", registerSub: "Create your account in minutes",
    emailLabel: "Email", passwordLabel: "Password", nameLabel: "Name",
    loginBtn: "Sign In", registerBtn: "Create Free Account",
    haveAccount: "Already have an account?", noAccount: "Don't have an account?",
    signIn: "Sign in", signUp: "Sign up",
    loading2: "Please wait…",
  },
};

export const THEMES = [
  { id: "nebula",    label: "Nebula",    dot: "🔵" },
  { id: "synthwave", label: "Synthwave", dot: "🟣" },
  { id: "midnight",  label: "Midnight",  dot: "⚫" },
  { id: "light",     label: "Light",     dot: "⚪" },
] as const;
