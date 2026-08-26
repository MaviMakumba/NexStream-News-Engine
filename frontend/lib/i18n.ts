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
    // ── Nav ──
    dashboard: "Haberler", search: "Arama", admin: "Yönetim", account: "Hesabım",
    login: "Giriş Yap", register: "Kayıt Ol", logout: "Çıkış",
    settings: "Ayarlar", theme: "Tema", language: "Dil", menu: "Menü",
    perfLabel: "Performans", perfLow: "Düşük", perfHigh: "Yüksek",
    perfLowDesc: "Tema animasyonlarında daha az parçacık — düşük donanımda daha akıcı",
    perfHighDesc: "Tema animasyonları tam yoğunlukta",

    // ── Theme names + moods (registry referenced) ──
    matrix: "Matrix", matrixTag: "Dijital Yağmur",
    godfather: "Godfather", godfatherTag: "Sinematik Sepya",
    cyberpunk: "Blade Runner", cyberpunkTag: "Neon Şehir",
    dune: "Dune", duneTag: "Çöl Fırtınası",
    starwars: "Star Wars", starwarsTag: "Hiperuzay",
    spiderman: "Spider-Man", spidermanTag: "Örümcek Ağı",
    batman: "Batman", batmanTag: "Gotham",
    wolfenstein: "Wolfenstein", wolfensteinTag: "Dizelpunk",
    day: "Aydınlık", dayTag: "Gündüz Modu",
    night: "Karanlık", nightTag: "Gece Modu",
    marketBist: "BİST100", marketUsd: "USD/TL", marketEur: "EUR/TL",
    marketGold: "Gram Altın", marketStale: "gecikmeli",

    // ── Dashboard ──
    trending: "Gündem", latestNews: "Son Haberler",
    allSources: "Tüm Kaynaklar", allQualities: "Tüm Kaliteler",
    qualityMed: "Orta+ (≥0.4)", qualityHigh: "Yüksek (≥0.6)",
    loadMore: "Daha fazla", loading: "Yükleniyor…",
    noTrending: "Gündem verisi yok",

    // ── Live ticker (WebSocket) ──
    liveOn: "Canlı", liveConnecting: "Bağlanıyor…", liveOff: "Bağlantı kesildi",
    liveWaiting: "Yeni haberler burada anında görünecek.",
    liveLocked: "Canlı haber akışı Pro plan özelliği.", liveUpgrade: "Yükselt",
    related: "İlgili haberler", hideRelated: "Gizle",
    relatedLocked: "İlişki grafı Pro plan özelliği.",
    loadingRelated: "Yükleniyor…", noRelated: "İlgili haber bulunamadı.",
    relatedError: "İlgili haberler yüklenemedi.",
    goToArticle: "Habere git →",
    saveArticle: "Kaydet", unsaveArticle: "Kaydedilenlerden kaldır",
    listenArticle: "Dinle", stopListening: "Durdur",
    savedPageTitle: "Kaydedilenler", savedPageDesc: "Sonra okumak için kaydettiğin haberler.",
    savedEmpty: "Henüz kaydedilen haber yok.",
    storySources: "Kaynaklar", hideSources: "Gizle", noSources: "Bu haberi doğrulayan başka kaynak bulunamadı.",
    sourcesError: "Kaynaklar yüklenemedi.",

    // ── Search ──
    searchPlaceholder: "bitcoin, deprem, yapay zeka…",
    searchBtn: "Ara", searchHistory: "Son aramalar", removeFromHistory: "Geçmişten kaldır",
    noResults: "için sonuç bulunamadı",
    semanticSearch: "Semantik Arama",
    semanticDesc: "Kelime tam eşleşmese de anlamsal olarak yakın haberler bulunur.",
    matchRate: "eşleşme", searchFailed: "Arama başarısız.",
    searchResultCapHint: "Ücretsiz planda sonuçlar 10 ile sınırlıdır — daha fazlası için Pro'ya geç.",

    // ── Auth ──
    loginTitle: "Tekrar Hoş Geldiniz", loginSub: "Hesabınıza giriş yapın",
    registerTitle: "Ücretsiz Başlayın", registerSub: "Dakikalar içinde hesap oluşturun",
    emailLabel: "E-posta", passwordLabel: "Şifre", nameLabel: "İsim",
    namePlaceholder: "Adınız Soyadınız", passwordHint: "En az 8 karakter",
    loginBtn: "Giriş Yap", registerBtn: "Kayıt Ol — Ücretsiz",
    haveAccount: "Zaten hesabınız var mı?", noAccount: "Hesabınız yok mu?",
    signIn: "Giriş yapın", signUp: "Kayıt olun",
    loading2: "Lütfen bekleyin…",
    loginFailed: "Giriş başarısız.", registerFailed: "Kayıt başarısız.",
    forgotPasswordLink: "Şifremi unuttum",
    forgotPasswordTitle: "Şifremi Unuttum", forgotPasswordSub: "E-posta adresinize bir sıfırlama bağlantısı gönderelim",
    forgotPasswordBtn: "Sıfırlama Bağlantısı Gönder",
    forgotPasswordSent: "Eğer bu e-posta kayıtlıysa, gelen kutunuza bir şifre sıfırlama bağlantısı gönderdik.",
    forgotPasswordFailed: "İstek gönderilemedi, lütfen tekrar deneyin.",
    backToLogin: "Girişe dön",
    resetPasswordTitle: "Yeni Şifre Belirle", resetPasswordSub: "Hesabınız için yeni bir şifre girin",
    newPasswordLabel: "Yeni Şifre", confirmPasswordLabel: "Yeni Şifre (Tekrar)",
    resetPasswordBtn: "Şifreyi Güncelle",
    resetPasswordSuccess: "Şifreniz güncellendi. Şimdi giriş yapabilirsiniz.",
    resetPasswordFailed: "Bağlantı geçersiz veya süresi dolmuş. Yeni bir bağlantı isteyin.",
    passwordsDontMatch: "Şifreler eşleşmiyor.",
    invalidResetLink: "Sıfırlama bağlantısı geçersiz.",
    goToLogin: "Girişe git",

    // ── E-posta doğrulama (v1.15) ──
    verifyBannerText: "E-posta adresini doğrulamadın. Free tier'da tam erişimin var, ama Pro/Kurumsal'a yükseltmek için doğrulama gerekiyor.",
    verifyBannerResend: "Doğrulama e-postası gönder",
    verifyBannerSent: "Doğrulama e-postası gönderildi, gelen kutunu kontrol et.",
    verifyBannerFailed: "Gönderilemedi, lütfen tekrar dene.",
    verifyEmailTitle: "E-posta Doğrulanıyor", verifyEmailSub: "Bağlantı kontrol ediliyor…",
    verifyEmailPending: "Doğrulanıyor…",
    verifyEmailSuccess: "E-postan doğrulandı! Artık Pro/Kurumsal'a yükseltebilirsin.",
    verifyEmailFailed: "Bu bağlantı geçersiz veya süresi dolmuş. Hesap sayfandan yenisini isteyebilirsin.",
    verifyEmailMissingToken: "Doğrulama bağlantısı eksik.",
    goToAccount: "Hesabıma git",
    upgradeNeedsVerification: "Yükseltmeden önce e-postanı doğrulaman gerekiyor.",

    // ── Landing ──
    heroBadge: "Canlı — 17 kaynaktan sürekli güncelleniyor",
    heroPre: "Türkiye Haberlerini ", heroAccent: "Yapay Zeka", heroPost: " ile Keşfet",
    heroSub: "17 kaynaktan gerçek zamanlı akış. Duygu analizi, entity tanıma, semantik arama ve ilişki grafı — tek platformda.",
    ctaPrimary: "Ücretsiz Başla →", ctaSecondary: "Demo Görüntüle",
    ctaAuthed: "Panele Git →", managePlan: "Planı Yönet",
    statArticles: "Haber İndekslendi", statSources: "Aktif Kaynak",
    statSpeed: "Analiz Süresi", statFree: "Ücretsiz Başlangıç",
    featuresLabel: "Özellikler", featuresTitle: "Güçlü Altyapı, Sinematik Arayüz",
    pricingLabel: "Fiyatlandırma", pricingTitle: "Ücretsiz başla, büyüdükçe yükselt",

    // ── Landing Search Demo ──
    landingSearchLabel: "CANLI DEMO — KAYIT GEREKMEZ",
    landingSearchTitle: "Klasik aramayı unutun. Ne anlama geldiğini arayın.",
    landingSearchPlaceholder: "örn. ekonomik kriz ve teknoloji şirketleri",
    landingSearchBtn: "Ara",
    landingSearchTryLabel: "Dene:",
    landingSearchEmpty: "Sonuç bulunamadı — farklı bir sorgu deneyin.",
    landingSearchErrorRateLimit: "Çok fazla arama denendi, birazdan tekrar deneyin.",
    landingSearchErrorGeneric: "Arama şu anda başarısız oldu, birazdan tekrar deneyin.",
    landingSearchSignupCta: "Tam deneyim için ücretsiz kaydolun →",
    landingSearchMatchRate: "eşleşme",
    mostPopular: "En Popüler", footerTagline: "AI Haber Motoru",
    privacy: "Gizlilik", terms: "Şartlar",
    agreeToTermsPrefix: "Kayıt olarak", agreeToTermsAnd: "ve",
    agreeToTermsSuffix: " kabul edersiniz.",
    termsLinkLabel: "Kullanım Şartları'nı", privacyLinkLabel: "Gizlilik Politikası'nı",

    // ── Account ──
    accountLabel: "Hesap", accountTitle: "Hesabım",
    planLabel: "Plan", apiLimitLabel: "API Limiti", includedFeatures: "Dahil Özellikler",
    upgradeTitle: "◈ Pro'ya Yükselt",
    upgradeDesc: "2.000 istek/gün, WebSocket canlı akış ve daha fazlası — aylık yalnızca $9.99.",
    proCta: "Pro — $9.99/ay", entCta: "Kurumsal — $49.99/ay",
    billingTitle: "Fatura Yönetimi", billingDesc: "Aboneliğinizi yönetin, faturalarınıza bakın.",
    billingPortal: "Fatura Portalı →", quickAccess: "Hızlı Erişim",
    usage: "Kullanım", sponsors: "Sponsorlar", apiDocs: "API Docs", rssFeed: "RSS Akışı",
    errorOccurred: "Hata oluştu.",

    // ── Hesap silme (v2.1.2) ──
    dangerZoneTitle: "Tehlikeli Bölge", dangerZoneDesc: "Hesabını sildiğinde tüm verilerin (oturumlar, API anahtarı, kullanım geçmişi, bülten aboneliği) kalıcı olarak silinir. Bu işlem geri alınamaz.",
    deleteAccountBtn: "Hesabımı Sil", deleteAccountCancel: "Vazgeç",
    deleteAccountConfirmTitle: "Emin misin?", deleteAccountPasswordLabel: "Devam etmek için parolanı gir",
    deleteAccountCheckboxLabel: "Bu işlemin geri alınamayacağını anlıyorum.",
    deleteAccountSubmit: "Kalıcı Olarak Sil", deleteAccountSubmitting: "Siliniyor…",
    deleteAccountOwnerNote: "Kurucu hesaplar bu sayfadan silinemez.",

    // ── Account: kullanım paneli & API anahtarı (v1.11) ──
    usageTitle: "Kullanım & Kota", usedToday: "Bugün Kullanılan",
    remainingToday: "Kalan", dailyLimitLabel: "Günlük Limit",
    unlimited: "Sınırsız", windowTotal: "istek (seçili aralık)",
    noUsage: "Henüz API kullanımı yok.",
    apiKeyTitle: "API Anahtarı",
    apiKeyDesc: "Kişisel anahtarınızla /api/v1 endpoint'lerine X-User-Key header'ı üzerinden erişin. Kota planınızdan düşer.",
    generateKey: "◈ Anahtar Üret", regenerateKey: "Yenile", revokeKey: "İptal Et",
    copyKey: "Kopyala", copied: "Kopyalandı ✓",
    noApiKey: "Henüz anahtar üretilmedi.",
    newsletterTitle: "Bülten Tercihleri",
    newsletterDesc: "Seçtiğin kaynak/konulara göre günlük özet e-postası al, ya da anahtar kelime eşleştiğinde anında haber olsun.",
    newsletterFreqLabel: "Sıklık", newsletterFreqDaily: "Günlük özet", newsletterFreqInstant: "Anlık uyarı", newsletterFreqNever: "Kapalı",
    newsletterFreqInstantLocked: "Anlık uyarı Pro plan gerektirir",
    newsletterTopicsLabel: "Konular (boş = hepsi)", newsletterSourcesLabel: "Kaynaklar (boş = hepsi)", newsletterKeywordsLabel: "Anahtar kelimeler",
    newsletterKeywordsPlaceholder: "örn. gram altın — yaz, Enter'a bas ya da Ekle'ye tıkla",
    newsletterKeywordAdd: "Ekle", newsletterKeywordRemove: "Kaldır",

    // ── RAG soru-cevap (roadmap #13) ──
    askNavLabel: "Soru Sor",
    askPageTitle: "Kanıta Dayalı Haber Asistanı",
    askPageDesc: "Takip ettiğimiz kaynaklara dayanarak soru sor — sadece elimizdeki kanıtı kullanır, uydurmaz.",
    askLocked: "Soru-cevap asistanı Pro plan gerektirir.",
    askPlaceholder: "Bir şey sor…",
    askSendBtn: "Gönder",
    askThinking: "Düşünüyor…",
    askEmptyState: "Henüz bir şey sormadın. Takip ettiğimiz haberler hakkında soru sorabilirsin.",
    askCoverageFull: "Tam kapsandı",
    askCoveragePartial: "Kısmen kapsandı",
    askCoverageNone: "Kanıt bulunamadı",
    askCorroborationMulti: "Birden fazla kaynak doğruluyor",
    askCorroborationSingle: "Tek kaynağa dayanıyor",
    askSuggestAlertBtn: "🔔 Bu konuda haber çıkarsa bildir",
    askErrorGeneric: "Şu an yanıt üretemiyorum, birazdan tekrar dene.",
    askBackToGeneral: "Genel sohbete dön",
    askSourcesLabel: "Kaynaklar:",
    askCardButton: "Sor",

    newsletterSave: "Kaydet", newsletterSaved: "Kaydedildi ✓", newsletterUnsubscribe: "Aboneliği İptal Et",
    newsletterSubscribedNote: "Şu an abonesin.", newsletterNotSubscribedNote: "Henüz abone değilsin.",
    pushLabel: "Bu tarayıcıda bildirimleri aç", pushSubscribedLabel: "Bu tarayıcıda bildirimler açık",
    pushErrorLabel: "Bildirim izni alınamadı, tekrar dener misin?",
    pushLockedReason: "Önce yukarıdan 'Anlık uyarı' seçip kaydetmelisin.",
    devModeBadge: "DEV MODE", devUpgraded: "Planınız yükseltildi (ödeme simülasyonu).",
    devDowngradeBtn: "Free'ye Dön (dev)", devDowngraded: "Planınız Free'ye düşürüldü.",

    // ── Ham veri export (v1.16) ──
    exportTitle: "Ham Veri Export", exportBadge: "KURUMSAL",
    exportDesc: "Tüm haber verinizi CSV veya JSON olarak indirin — başlık, içerik, duygu analizi, entity ve kalite skorları dahil.",
    exportFormatLabel: "Format", exportDownloadBtn: "İndir",
    exportRowCapNote: "Tek indirmede en fazla 20.000 satır döner. Daha fazla filtreleme için /api/v1/news/export endpoint'ini doğrudan kullanın.",

    // ── Admin ──
    adminTitle: "🔧 Yönetim Paneli", adminSub: "Admin yetkisi veya API anahtarı gereklidir.",
    adminAsUser: "Admin oturumuyla görüntülüyorsunuz — anahtar gerekmez.",
    adminKey: "Admin API Anahtarı", dayRange: "Gün Aralığı", dayUnit: "gün",
    show: "Göster", loadingShort: "Yükleniyor…", accessDenied: "Erişim reddedildi.",
    accessDeniedDesc: "Bu sayfayı görüntülemek için yönetici veya moderatör yetkisi gerekir.",
    totalReq: "Toplam İstek", uniqueEndpoint: "Benzersiz Endpoint", avgResp: "Ort. Yanıt Süresi",
    colUserId: "User ID", colEndpoint: "Endpoint", colReq: "İstek", colAvgMs: "Ort. ms",
    noRecords: "Kayıt bulunamadı.", anon: "anonim",
    currentSponsors: "Mevcut Sponsorlar", newSponsor: "Yeni Sponsor",
    activeStatus: "Aktif", passiveStatus: "Pasif", deactivate: "Deaktif Et",
    activateSponsor: "Aktifleştir", deletePermanently: "Sil",
    deleteSponsorConfirm: "Bu sponsoru kalıcı olarak silmek istediğinize emin misiniz? Bu işlem geri alınamaz.",
    noSponsors: "Henüz sponsor yok.", sponsorName: "Sponsor Adı",
    messageLabel: "Mesaj", startLabel: "Başlangıç", endLabel: "Bitiş",
    addSponsor: "◈ Sponsor Ekle", saving: "Kaydediliyor…",
    sponsorMsgPlaceholder: "Sponsor mesajı...", genericError: "Hata.",

    // ── Admin: kullanıcı/müşteri listesi ──
    users: "Kullanıcılar",
    usersTitle: "Kullanıcılar & Ödeme Durumu",
    tierFilter: "Tier Filtresi", allTiers: "Tüm Tier'lar",
    colEmail: "E-posta", colTier: "Tier", colStatus: "Durum", colPaying: "Ödeme", colJoined: "Kayıt",
    colRole: "Rol", colEmailVerified: "E-posta Doğrulama",
    payingReal: "✓ Stripe", payingDev: "Dev-mode", inactiveStatus: "Pasif",
    emailVerifiedYes: "✓ Doğrulandı", emailVerifiedNo: "Doğrulanmadı",
    totalUsers: "Toplam Kullanıcı", payingUsers: "Gerçek Ödeyen",
    noUsers: "Kullanıcı bulunamadı.",
    roleUser: "Kullanıcı", roleModerator: "Moderatör", roleAdmin: "Admin", roleOwner: "Kurucu",
    ownerBadge: "Kurucu",
    roleUpdateError: "Rol değiştirilemedi.", tierUpdateError: "Tier değiştirilemedi.",
    banUser: "Banla", unbanUser: "Banı Kaldır",
    banUserConfirm: "Bu kullanıcıyı banlamak istediğinize emin misiniz? Tüm oturumları anında kapanır.",
    activeUpdateError: "Durum değiştirilemedi.",
  },
  EN: {
    // ── Nav ──
    dashboard: "News", search: "Search", admin: "Admin", account: "Account",
    login: "Sign In", register: "Register", logout: "Log Out",
    settings: "Settings", theme: "Theme", language: "Language", menu: "Menu",
    perfLabel: "Performance", perfLow: "Low", perfHigh: "High",
    perfLowDesc: "Fewer particles in theme animations — smoother on low-end hardware",
    perfHighDesc: "Theme animations run at full density",

    // ── Theme names + moods ──
    matrix: "Matrix", matrixTag: "Digital Rain",
    godfather: "Godfather", godfatherTag: "Cinematic Sepia",
    cyberpunk: "Blade Runner", cyberpunkTag: "Neon City",
    dune: "Dune", duneTag: "Desert Storm",
    starwars: "Star Wars", starwarsTag: "Hyperspace",
    spiderman: "Spider-Man", spidermanTag: "Web Slinger",
    batman: "Batman", batmanTag: "Gotham",
    wolfenstein: "Wolfenstein", wolfensteinTag: "Dieselpunk",
    day: "Daylight", dayTag: "Day Mode",
    night: "Nightfall", nightTag: "Night Mode",
    marketBist: "BIST100", marketUsd: "USD/TRY", marketEur: "EUR/TRY",
    marketGold: "Gold (gram)", marketStale: "delayed",

    // ── Dashboard ──
    trending: "Trending", latestNews: "Latest News",
    allSources: "All Sources", allQualities: "All Qualities",
    qualityMed: "Medium+ (≥0.4)", qualityHigh: "High (≥0.6)",
    loadMore: "Load more", loading: "Loading…",
    noTrending: "No trending data",

    // ── Live ticker (WebSocket) ──
    liveOn: "Live", liveConnecting: "Connecting…", liveOff: "Disconnected",
    liveWaiting: "New articles will appear here instantly.",
    liveLocked: "Live news stream is a Pro plan feature.", liveUpgrade: "Upgrade",
    related: "Related articles", hideRelated: "Hide",
    relatedLocked: "Relation graph is a Pro plan feature.",
    loadingRelated: "Loading…", noRelated: "No related articles found.",
    relatedError: "Failed to load related articles.",
    goToArticle: "Read article →",
    saveArticle: "Save", unsaveArticle: "Remove from saved",
    listenArticle: "Listen", stopListening: "Stop",
    savedPageTitle: "Saved Articles", savedPageDesc: "Articles you saved to read later.",
    savedEmpty: "No saved articles yet.",
    storySources: "Sources", hideSources: "Hide", noSources: "No other source confirming this story was found.",
    sourcesError: "Failed to load sources.",

    // ── Search ──
    searchPlaceholder: "bitcoin, earthquake, AI…",
    searchBtn: "Search", searchHistory: "Recent searches", removeFromHistory: "Remove from history",
    noResults: "no results for",
    semanticSearch: "Semantic Search",
    semanticDesc: "Finds semantically similar articles even without exact keyword matches.",
    matchRate: "match", searchFailed: "Search failed.",
    searchResultCapHint: "Free plan is limited to 10 results — go Pro for more.",

    // ── Auth ──
    loginTitle: "Welcome Back", loginSub: "Sign in to your account",
    registerTitle: "Start for Free", registerSub: "Create your account in minutes",
    emailLabel: "Email", passwordLabel: "Password", nameLabel: "Name",
    namePlaceholder: "Your full name", passwordHint: "At least 8 characters",
    loginBtn: "Sign In", registerBtn: "Create Free Account",
    haveAccount: "Already have an account?", noAccount: "Don't have an account?",
    signIn: "Sign in", signUp: "Sign up",
    loading2: "Please wait…",
    loginFailed: "Sign in failed.", registerFailed: "Registration failed.",
    forgotPasswordLink: "Forgot password?",
    forgotPasswordTitle: "Forgot Password", forgotPasswordSub: "We'll send a reset link to your email",
    forgotPasswordBtn: "Send Reset Link",
    forgotPasswordSent: "If that email is registered, we've sent a password reset link to your inbox.",
    forgotPasswordFailed: "Couldn't send the request, please try again.",
    backToLogin: "Back to sign in",
    resetPasswordTitle: "Set New Password", resetPasswordSub: "Enter a new password for your account",
    newPasswordLabel: "New Password", confirmPasswordLabel: "Confirm New Password",
    resetPasswordBtn: "Update Password",
    resetPasswordSuccess: "Your password has been updated. You can sign in now.",
    resetPasswordFailed: "This link is invalid or expired. Please request a new one.",
    passwordsDontMatch: "Passwords don't match.",
    invalidResetLink: "The reset link is invalid.",
    goToLogin: "Go to sign in",

    // ── Email verification (v1.15) ──
    verifyBannerText: "Your email isn't verified yet. You have full Free tier access, but verification is required to upgrade to Pro/Enterprise.",
    verifyBannerResend: "Send verification email",
    verifyBannerSent: "Verification email sent, check your inbox.",
    verifyBannerFailed: "Couldn't send it, please try again.",
    verifyEmailTitle: "Verifying Email", verifyEmailSub: "Checking your link…",
    verifyEmailPending: "Verifying…",
    verifyEmailSuccess: "Your email is verified! You can now upgrade to Pro/Enterprise.",
    verifyEmailFailed: "This link is invalid or expired. You can request a new one from your account page.",
    verifyEmailMissingToken: "Verification link is missing.",
    goToAccount: "Go to my account",
    upgradeNeedsVerification: "You need to verify your email before upgrading.",

    // ── Landing ──
    heroBadge: "Live — continuously updated from 17 sources",
    heroPre: "Discover the News with ", heroAccent: "Artificial Intelligence", heroPost: "",
    heroSub: "Real-time stream from 17 sources. Sentiment analysis, entity recognition, semantic search and a relation graph — all in one platform.",
    ctaPrimary: "Start Free →", ctaSecondary: "View Demo",
    ctaAuthed: "Go to Dashboard →", managePlan: "Manage Plan",
    statArticles: "Articles Indexed", statSources: "Active Sources",
    statSpeed: "Analysis Time", statFree: "Free to Start",
    featuresLabel: "Features", featuresTitle: "Powerful Engine, Cinematic Interface",
    pricingLabel: "Pricing", pricingTitle: "Start free, upgrade as you grow",

    // ── Landing Search Demo ──
    landingSearchLabel: "LIVE DEMO — NO SIGN-UP NEEDED",
    landingSearchTitle: "Forget keyword search. Search for what it means.",
    landingSearchPlaceholder: "e.g. economic crisis and tech companies",
    landingSearchBtn: "Search",
    landingSearchTryLabel: "Try:",
    landingSearchEmpty: "No results found — try a different query.",
    landingSearchErrorRateLimit: "Too many searches, please try again shortly.",
    landingSearchErrorGeneric: "Search failed right now, please try again shortly.",
    landingSearchSignupCta: "Sign up free for the full experience →",
    landingSearchMatchRate: "match",
    mostPopular: "Most Popular", footerTagline: "AI News Engine",
    privacy: "Privacy", terms: "Terms",
    agreeToTermsPrefix: "By signing up, you agree to our", agreeToTermsAnd: "and",
    agreeToTermsSuffix: ".",
    termsLinkLabel: "Terms of Service", privacyLinkLabel: "Privacy Policy",

    // ── Account ──
    accountLabel: "Account", accountTitle: "My Account",
    planLabel: "Plan", apiLimitLabel: "API Limit", includedFeatures: "Included Features",
    upgradeTitle: "◈ Upgrade to Pro",
    upgradeDesc: "2,000 req/day, WebSocket live stream and more — just $9.99/month.",
    proCta: "Pro — $9.99/mo", entCta: "Enterprise — $49.99/mo",
    billingTitle: "Billing", billingDesc: "Manage your subscription and invoices.",
    billingPortal: "Billing Portal →", quickAccess: "Quick Access",
    usage: "Usage", sponsors: "Sponsors", apiDocs: "API Docs", rssFeed: "RSS Feed",
    errorOccurred: "An error occurred.",

    // ── Account deletion (v2.1.2) ──
    dangerZoneTitle: "Danger Zone", dangerZoneDesc: "Deleting your account permanently removes all your data (sessions, API key, usage history, newsletter subscription). This cannot be undone.",
    deleteAccountBtn: "Delete My Account", deleteAccountCancel: "Cancel",
    deleteAccountConfirmTitle: "Are you sure?", deleteAccountPasswordLabel: "Enter your password to continue",
    deleteAccountCheckboxLabel: "I understand this cannot be undone.",
    deleteAccountSubmit: "Permanently Delete", deleteAccountSubmitting: "Deleting…",
    deleteAccountOwnerNote: "Founder accounts cannot be deleted from this page.",

    // ── Account: usage panel & API key (v1.11) ──
    usageTitle: "Usage & Quota", usedToday: "Used Today",
    remainingToday: "Remaining", dailyLimitLabel: "Daily Limit",
    unlimited: "Unlimited", windowTotal: "requests (selected range)",
    noUsage: "No API usage yet.",
    apiKeyTitle: "API Key",
    apiKeyDesc: "Access /api/v1 endpoints with your personal key via the X-User-Key header. Usage counts against your plan quota.",
    generateKey: "◈ Generate Key", regenerateKey: "Rotate", revokeKey: "Revoke",
    copyKey: "Copy", copied: "Copied ✓",
    noApiKey: "No key generated yet.",
    newsletterTitle: "Newsletter Preferences",
    newsletterDesc: "Get a daily digest based on your chosen sources/topics, or instant alerts when a keyword matches.",
    newsletterFreqLabel: "Frequency", newsletterFreqDaily: "Daily digest", newsletterFreqInstant: "Instant alerts", newsletterFreqNever: "Off",
    newsletterFreqInstantLocked: "Instant alerts require a Pro plan",
    newsletterTopicsLabel: "Topics (empty = all)", newsletterSourcesLabel: "Sources (empty = all)", newsletterKeywordsLabel: "Keywords",
    newsletterKeywordsPlaceholder: "e.g. gram gold — type, press Enter, or click Add",
    newsletterKeywordAdd: "Add", newsletterKeywordRemove: "Remove",

    // ── RAG Q&A (roadmap #13) ──
    askNavLabel: "Ask",
    askPageTitle: "Evidence-Grounded News Assistant",
    askPageDesc: "Ask a question grounded in the sources we track — it only uses the evidence we have, never makes things up.",
    askLocked: "The Q&A assistant requires a Pro plan.",
    askPlaceholder: "Ask something…",
    askSendBtn: "Send",
    askThinking: "Thinking…",
    askEmptyState: "You haven't asked anything yet. Ask about the news we track.",
    askCoverageFull: "Fully covered",
    askCoveragePartial: "Partially covered",
    askCoverageNone: "No evidence found",
    askCorroborationMulti: "Confirmed by multiple sources",
    askCorroborationSingle: "Based on a single source",
    askSuggestAlertBtn: "🔔 Notify me if news breaks on this",
    askErrorGeneric: "I can't answer right now, please try again shortly.",
    askBackToGeneral: "Back to general chat",
    askSourcesLabel: "Sources:",
    askCardButton: "Ask",

    newsletterSave: "Save", newsletterSaved: "Saved ✓", newsletterUnsubscribe: "Unsubscribe",
    newsletterSubscribedNote: "You're currently subscribed.", newsletterNotSubscribedNote: "You're not subscribed yet.",
    pushLabel: "Enable notifications in this browser", pushSubscribedLabel: "Notifications are on in this browser",
    pushErrorLabel: "Couldn't get notification permission, try again?",
    pushLockedReason: "First select 'Instant alerts' above and save.",
    devModeBadge: "DEV MODE", devUpgraded: "Your plan was upgraded (payment simulation).",
    devDowngradeBtn: "Back to Free (dev)", devDowngraded: "Your plan was downgraded to Free.",

    // ── Raw data export (v1.16) ──
    exportTitle: "Raw Data Export", exportBadge: "ENTERPRISE",
    exportDesc: "Download your entire news archive as CSV or JSON — title, content, sentiment, entities and quality scores included.",
    exportFormatLabel: "Format", exportDownloadBtn: "Download",
    exportRowCapNote: "A single download returns up to 20,000 rows. For more granular filtering, use the /api/v1/news/export endpoint directly.",

    // ── Admin ──
    adminTitle: "🔧 Admin Panel", adminSub: "Admin role or API key required.",
    adminAsUser: "Viewing with your admin session — no key needed.",
    adminKey: "Admin API Key", dayRange: "Day Range", dayUnit: "days",
    show: "Show", loadingShort: "Loading…", accessDenied: "Access denied.",
    accessDeniedDesc: "You need admin or moderator privileges to view this page.",
    totalReq: "Total Requests", uniqueEndpoint: "Unique Endpoints", avgResp: "Avg Response Time",
    colUserId: "User ID", colEndpoint: "Endpoint", colReq: "Requests", colAvgMs: "Avg ms",
    noRecords: "No records found.", anon: "anonymous",
    currentSponsors: "Current Sponsors", newSponsor: "New Sponsor",
    activeStatus: "Active", passiveStatus: "Inactive", deactivate: "Deactivate",
    activateSponsor: "Activate", deletePermanently: "Delete",
    deleteSponsorConfirm: "Are you sure you want to permanently delete this sponsor? This cannot be undone.",
    noSponsors: "No sponsors yet.", sponsorName: "Sponsor Name",
    messageLabel: "Message", startLabel: "Start", endLabel: "End",
    addSponsor: "◈ Add Sponsor", saving: "Saving…",
    sponsorMsgPlaceholder: "Sponsor message...", genericError: "Error.",

    // ── Admin: user/customer list ──
    users: "Users",
    usersTitle: "Users & Payment Status",
    tierFilter: "Tier Filter", allTiers: "All Tiers",
    colEmail: "Email", colTier: "Tier", colStatus: "Status", colPaying: "Payment", colJoined: "Joined",
    colRole: "Role", colEmailVerified: "Email Verification",
    payingReal: "✓ Stripe", payingDev: "Dev-mode", inactiveStatus: "Inactive",
    emailVerifiedYes: "✓ Verified", emailVerifiedNo: "Unverified",
    totalUsers: "Total Users", payingUsers: "Real Paying",
    noUsers: "No users found.",
    roleUser: "User", roleModerator: "Moderator", roleAdmin: "Admin", roleOwner: "Owner",
    ownerBadge: "Founder",
    roleUpdateError: "Could not update role.", tierUpdateError: "Could not update tier.",
    banUser: "Ban", unbanUser: "Unban",
    banUserConfirm: "Are you sure you want to ban this user? All their sessions end immediately.",
    activeUpdateError: "Could not update status.",
  },
};

// ── Structured landing content (localized) ──────────────────────────

/** Landing arama demosundaki tıklanabilir örnek sorgu chip'leri. */
export const LANDING_SEARCH_EXAMPLES: Record<Lang, string[]> = {
  TR: ["ekonomik kriz ve teknoloji şirketleri", "yapay zeka düzenlemeleri", "İstanbul deprem riski"],
  EN: ["economic crisis and tech companies", "AI regulation", "climate change summit"],
};

export interface Feature { icon: string; accent: string; title: string; desc: string; }

export const FEATURES: Record<Lang, Feature[]> = {
  TR: [
    { icon: "◈", accent: "var(--accent)",  title: "AI Sentiment Analizi", desc: "Groq llama-3.1 ile her haberin duygu durumu, entity tanıma ve konu sınıflandırması saniyeler içinde." },
    { icon: "⬡", accent: "var(--accent2)", title: "Semantik Arama",       desc: "ChromaDB vektör veritabanı ile anlamsal arama — aradığın kelime haberde olmasa bile bulur." },
    { icon: "◎", accent: "var(--pos)",     title: "Canlı Haber Akışı",     desc: "WebSocket ile yeni haberler anında ekrana düşüyor. 17 kaynak, sürekli güncellenen feed." },
  ],
  EN: [
    { icon: "◈", accent: "var(--accent)",  title: "AI Sentiment Analysis", desc: "Sentiment, entity recognition and topic classification for every article in seconds, powered by Groq llama-3.1." },
    { icon: "⬡", accent: "var(--accent2)", title: "Semantic Search",       desc: "Vector search with ChromaDB — finds the right articles even when your exact keyword isn't in the text." },
    { icon: "◎", accent: "var(--pos)",     title: "Live News Stream",      desc: "New articles hit the screen instantly over WebSocket. 17 sources, a continuously updated feed." },
  ],
};

export interface Plan {
  tier: string; price: string; period: string;
  features: string[]; cta: string; href: string; highlight: boolean;
}

export const PRICING: Record<Lang, Plan[]> = {
  TR: [
    { tier: "Ücretsiz", price: "$0", period: "", highlight: false, href: "/auth/register", cta: "Hemen Başla",
      features: ["100 API isteği / gün", "Haberler & semantik arama", "Günlük digest e-posta", "10 arama sonucu"] },
    { tier: "Pro", price: "$9.99", period: "/ay", highlight: true, href: "/auth/register", cta: "Pro'ya Geç",
      features: ["2.000 API isteği / gün", "WebSocket canlı akış", "50 arama sonucu", "Anlık keyword alert", "İlişki grafı"] },
    { tier: "Kurumsal", price: "$49.99", period: "/ay", highlight: false, href: "/auth/register", cta: "İletişime Geç",
      features: ["Sınırsız API isteği", "Ham veri export", "Özel kaynak talebi (bize ulaşın)", "SLA garantisi", "Öncelikli destek"] },
  ],
  EN: [
    { tier: "Free", price: "$0", period: "", highlight: false, href: "/auth/register", cta: "Get Started",
      features: ["100 API requests / day", "News & semantic search", "Daily digest email", "10 search results"] },
    { tier: "Pro", price: "$9.99", period: "/mo", highlight: true, href: "/auth/register", cta: "Go Pro",
      features: ["2,000 API requests / day", "WebSocket live stream", "50 search results", "Instant keyword alerts", "Relation graph"] },
    { tier: "Enterprise", price: "$49.99", period: "/mo", highlight: false, href: "/auth/register", cta: "Contact Us",
      features: ["Unlimited API requests", "Raw data export", "Custom source requests (contact us)", "SLA guarantee", "Priority support"] },
  ],
};

// ── Account tier detail (localized) ─────────────────────────────────

export interface TierDetail { limit: string; icon: string; color: string; features: string[]; }

export const TIER_DETAILS: Record<Lang, Record<string, TierDetail>> = {
  TR: {
    free:       { limit: "100 istek / gün",   icon: "○", color: "var(--text2)",   features: ["Haberler & arama", "10 arama sonucu", "Günlük digest e-posta"] },
    pro:        { limit: "2.000 istek / gün", icon: "◈", color: "var(--accent)",  features: ["Tüm Ücretsiz özellikler", "WebSocket canlı akış", "50 arama sonucu", "İlişki grafı"] },
    enterprise: { limit: "Sınırsız",          icon: "◆", color: "var(--accent2)", features: ["Tüm Pro özellikler", "Ham veri export", "Özel kaynak talebi (bize ulaşın)", "SLA garantisi"] },
  },
  EN: {
    free:       { limit: "100 req / day",     icon: "○", color: "var(--text2)",   features: ["News & search", "10 search results", "Daily digest email"] },
    pro:        { limit: "2,000 req / day",   icon: "◈", color: "var(--accent)",  features: ["All Free features", "WebSocket live stream", "50 search results", "Relation graph"] },
    enterprise: { limit: "Unlimited",         icon: "◆", color: "var(--accent2)", features: ["All Pro features", "Raw data export", "Custom source requests (contact us)", "SLA guarantee"] },
  },
};
