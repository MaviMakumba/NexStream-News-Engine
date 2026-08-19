import type { Lang } from "./settings-context";

// Gizlilik/Şartlar sayfalarının uzun biçimli içeriği — `lib/i18n.ts`'in düz
// UI sözlüğüne değil (paragraf uzunluğunda değerler o dosyanın "kısa
// etiket" konvansiyonunu bozar), FEATURES/PRICING ile aynı yapılandırılmış
// desene konur.

export interface LegalSection {
  heading: string;
  body: string;
}

export interface LegalPage {
  title: string;
  updated: string;
  disclaimer: string;
  sections: LegalSection[];
}

export const PRIVACY_POLICY: Record<Lang, LegalPage> = {
  TR: {
    title: "Gizlilik Politikası",
    updated: "Son güncelleme: Temmuz 2026",
    disclaimer:
      "⚠ Bu sayfa bir başlangıç şablonudur — gerçek yayın öncesi mutlaka bir hukuk danışmanı tarafından incelenmelidir. Bağlayıcı bir hukuki belge değildir.",
    sections: [
      {
        heading: "Hangi verileri topluyoruz?",
        body:
          "Hesap oluşturduğunuzda e-posta adresinizi, adınızı (isteğe bağlı) ve şifrenizi (bcrypt ile geri döndürülemez şekilde hash'lenmiş olarak, asla düz metin saklanmaz) topluyoruz. Oturumunuzu sürdürmek için tarayıcınıza HttpOnly, yalnızca sunucunun okuyabildiği bir çerez (nxs_session) yerleştiriyoruz — bu çerez JavaScript tarafından okunamaz ve üçüncü taraflarla paylaşılmaz.",
      },
      {
        heading: "Üçüncü taraf hizmet sağlayıcılar",
        body:
          "Haber analizi için Groq'un yapay zeka API'sini kullanıyoruz (yalnızca kazınan haber metinleri işlenir, kişisel verileriniz gönderilmez). Şifre sıfırlama ve bülten e-postaları Resend üzerinden gönderilir. Ödeme işlemleri (ücretli planlar) Stripe üzerinden yürütülür; kart bilgileriniz bizim sunucularımıza hiç ulaşmaz.",
      },
      {
        heading: "Verilerinizi nasıl kullanıyoruz?",
        body:
          "Toplanan veriler yalnızca hesabınızı işletmek, kullanım kotanızı hesaplamak, tercih ettiğiniz bildirimleri göndermek ve hizmeti iyileştirmek için kullanılır. Verileriniz satılmaz veya reklam amacıyla üçüncü taraflarla paylaşılmaz.",
      },
      {
        heading: "Haklarınız",
        body:
          "Hesap bilgilerinizi Hesabım sayfasından görüntüleyebilir, API anahtarınızı istediğiniz zaman iptal edebilir ve hesabınızı (Hesabım sayfasındaki \"Tehlikeli Bölge\" bölümünden) kalıcı olarak silebilirsiniz — hesap silindiğinde oturumlarınız, API anahtarınız, kullanım geçmişiniz ve bülten aboneliğiniz dahil tüm verileriniz veritabanından tamamen kaldırılır ve bu işlem geri alınamaz.",
      },
      {
        heading: "Çerezler",
        body:
          "Yalnızca oturumunuzu sürdürmek için zorunlu bir çerez (nxs_session) ve tema/dil tercihiniz için tarayıcınızın yerel depolamasını (localStorage) kullanıyoruz. Takip veya reklam amaçlı çerez kullanılmıyor.",
      },
    ],
  },
  EN: {
    title: "Privacy Policy",
    updated: "Last updated: July 2026",
    disclaimer:
      "⚠ This page is a starter template — it must be reviewed by legal counsel before real public launch. It is not a binding legal document.",
    sections: [
      {
        heading: "What data do we collect?",
        body:
          "When you create an account we collect your email address, your name (optional), and your password (hashed irreversibly with bcrypt, never stored in plain text). To keep you signed in we place an HttpOnly, server-only session cookie (nxs_session) in your browser — it cannot be read by JavaScript and is never shared with third parties.",
      },
      {
        heading: "Third-party service providers",
        body:
          "We use Groq's AI API for news analysis (only scraped article text is processed, never your personal data). Password-reset and digest emails are sent via Resend. Payments (paid plans) are processed via Stripe; your card details never reach our servers.",
      },
      {
        heading: "How we use your data",
        body:
          "Collected data is used solely to operate your account, calculate your usage quota, deliver notifications you've opted into, and improve the service. Your data is never sold or shared with third parties for advertising.",
      },
      {
        heading: "Your rights",
        body:
          "You can view your account details, revoke your API key at any time, and permanently delete your account from the \"Danger Zone\" section on the Account page — deleting your account permanently removes all your data from our database, including sessions, your API key, usage history, and newsletter subscription, and this action cannot be undone.",
      },
      {
        heading: "Cookies",
        body:
          "We only use one essential cookie to keep you signed in (nxs_session) and your browser's local storage for your theme/language preference. No tracking or advertising cookies are used.",
      },
    ],
  },
};

export const TERMS_OF_SERVICE: Record<Lang, LegalPage> = {
  TR: {
    title: "Kullanım Şartları",
    updated: "Son güncelleme: Temmuz 2026",
    disclaimer:
      "⚠ Bu sayfa bir başlangıç şablonudur — gerçek yayın öncesi mutlaka bir hukuk danışmanı tarafından incelenmelidir. Bağlayıcı bir hukuki belge değildir.",
    sections: [
      {
        heading: "Hizmetin kapsamı",
        body:
          "NexStream, yapay zeka destekli haber analizi (duygu analizi, semantik arama, ilişki grafı) sunan bir platformdur. Ücretsiz planda günlük kullanım kotası uygulanır; ücretli planlar daha yüksek kota ve ek özellikler sunar.",
      },
      {
        heading: "Hesabınız",
        body:
          "Hesabınızın güvenliğinden (şifrenizin gizliliği dahil) siz sorumlusunuz. Hesabınız altında gerçekleşen tüm etkinliklerden sorumlu tutulursunuz. Şüpheli bir erişim fark ederseniz bizimle iletişime geçin.",
      },
      {
        heading: "Kabul edilebilir kullanım",
        body:
          "Hizmeti yasa dışı amaçlarla, otomatik kötüye kullanım (rate limit'leri aşmaya yönelik sistematik girişimler dahil) veya başkalarının haklarını ihlal edecek şekilde kullanamazsınız. Kurallara uyulmaması hesabın askıya alınmasına yol açabilir.",
      },
      {
        heading: "İçerik ve doğruluk",
        body:
          "Haber özetleri ve duygu analizleri yapay zeka tarafından otomatik olarak üretilir ve hata içerebilir. NexStream, üçüncü taraf haber kaynaklarının içeriğinin doğruluğunu garanti etmez; haberler orijinal kaynağa atıfla sunulur.",
      },
      {
        heading: "Değişiklikler",
        body:
          "Bu şartları zaman zaman güncelleyebiliriz. Önemli değişiklikler hesabınızla ilişkili e-posta adresine bildirilecektir.",
      },
    ],
  },
  EN: {
    title: "Terms of Service",
    updated: "Last updated: July 2026",
    disclaimer:
      "⚠ This page is a starter template — it must be reviewed by legal counsel before real public launch. It is not a binding legal document.",
    sections: [
      {
        heading: "Scope of the service",
        body:
          "NexStream is a platform offering AI-powered news analysis (sentiment analysis, semantic search, relationship graphs). The Free plan applies a daily usage quota; paid plans offer higher quotas and additional features.",
      },
      {
        heading: "Your account",
        body:
          "You are responsible for the security of your account, including keeping your password confidential. You are responsible for all activity under your account. Contact us if you notice suspicious access.",
      },
      {
        heading: "Acceptable use",
        body:
          "You may not use the service for unlawful purposes, systematic automated abuse (including attempts to bypass rate limits), or in a way that infringes on others' rights. Violations may result in account suspension.",
      },
      {
        heading: "Content and accuracy",
        body:
          "News summaries and sentiment analyses are generated automatically by AI and may contain errors. NexStream does not guarantee the accuracy of third-party news source content; articles are presented with attribution to their original source.",
      },
      {
        heading: "Changes",
        body:
          "We may update these terms from time to time. Material changes will be notified to the email address associated with your account.",
      },
    ],
  },
};
