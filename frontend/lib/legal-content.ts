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
    updated: "Son güncelleme: Ağustos 2026",
    disclaimer:
      "⚠ Bu sayfa bir başlangıç şablonudur — gerçek yayın öncesi mutlaka bir hukuk danışmanı tarafından incelenmelidir. Bağlayıcı bir hukuki belge değildir.",
    sections: [
      {
        heading: "Hangi verileri topluyoruz?",
        body:
          "Hesap oluşturduğunuzda e-posta adresinizi, adınızı (isteğe bağlı) ve şifrenizi (bcrypt ile geri döndürülemez şekilde hash'lenmiş olarak, asla düz metin saklanmaz) topluyoruz. Oturumunuzu sürdürmek için tarayıcınıza HttpOnly, yalnızca sunucunun okuyabildiği bir çerez (nxs_session) yerleştiriyoruz — bu çerez JavaScript tarafından okunamaz ve üçüncü taraflarla paylaşılmaz. Güvenlik amacıyla giriş, kayıt, şifre sıfırlama gibi hesap olaylarını IP adresi ve tarayıcı bilgisiyle birlikte bir güvenlik günlüğüne yazıyoruz; bu kayıtlar 90 gün sonra otomatik silinir ve yalnızca kötüye kullanım tespiti için kullanılır.",
      },
      {
        heading: "Üçüncü taraf hizmet sağlayıcılar",
        body:
          "Haber analizi için Groq'un yapay zeka API'sini kullanıyoruz (yalnızca kazınan haber metinleri işlenir, kişisel verileriniz gönderilmez). Şifre sıfırlama ve bülten e-postaları Resend üzerinden gönderilir. Ödeme işlemleri (ücretli planlar) Stripe üzerinden yürütülür; kart bilgileriniz bizim sunucularımıza hiç ulaşmaz. Hizmeti iyileştirmek için (yapılandırıldığında) Sentry hata takibi ve PostHog kullanım analitiği kullanılabilir — ikisi de reklam amaçlı DEĞİL, teknik hata ayıklama ve hangi özelliklerin kullanıldığını anlamak içindir.",
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
          "Oturumunuzu sürdürmek için zorunlu bir çerez (nxs_session) ve tema/dil tercihiniz için tarayıcınızın yerel depolamasını (localStorage) kullanıyoruz. Kullanım analitiği (PostHog) yapılandırıldığında sayfa gezinmeleri gibi anonim kullanım verileri de toplanabilir — reklam amaçlı çerez şu an KULLANILMIYOR, ileride eklenirse bu sayfa önceden güncellenir ve gerekli açık rıza mekanizması eklenir.",
      },
    ],
  },
  EN: {
    title: "Privacy Policy",
    updated: "Last updated: August 2026",
    disclaimer:
      "⚠ This page is a starter template — it must be reviewed by legal counsel before real public launch. It is not a binding legal document.",
    sections: [
      {
        heading: "What data do we collect?",
        body:
          "When you create an account we collect your email address, your name (optional), and your password (hashed irreversibly with bcrypt, never stored in plain text). To keep you signed in we place an HttpOnly, server-only session cookie (nxs_session) in your browser — it cannot be read by JavaScript and is never shared with third parties. For security we record account events such as sign-in, registration and password reset in a security log together with the IP address and browser information; these records are deleted automatically after 90 days and are used only to detect abuse.",
      },
      {
        heading: "Third-party service providers",
        body:
          "We use Groq's AI API for news analysis (only scraped article text is processed, never your personal data). Password-reset and digest emails are sent via Resend. Payments (paid plans) are processed via Stripe; your card details never reach our servers. When configured, we may use Sentry for error tracking and PostHog for usage analytics to improve the service — neither is used for advertising, only for technical debugging and understanding which features are used.",
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
          "We use one essential cookie to keep you signed in (nxs_session) and your browser's local storage for your theme/language preference. When usage analytics (PostHog) is configured, anonymous usage data such as page views may also be collected — advertising cookies are NOT currently used; if that changes, this page will be updated in advance with the appropriate consent mechanism.",
      },
    ],
  },
};

export const TERMS_OF_SERVICE: Record<Lang, LegalPage> = {
  TR: {
    title: "Kullanım Şartları",
    updated: "Son güncelleme: Ağustos 2026",
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
          "Hizmeti yasa dışı amaçlarla, otomatik kötüye kullanım (rate limit'leri aşmaya yönelik sistematik girişimler dahil) veya başkalarının haklarını ihlal edecek şekilde kullanamazsınız. Yazılı iznimiz olmadan sistem üzerinde sızma testi, zafiyet taraması, parola deneme (brute force), başkasının e-posta adresi ya da hesabı adına işlem yapma ve otomatik tarama yapamazsınız; bu tür eylemler Türk Ceza Kanunu'nun 243 ve 244. maddeleri kapsamında suç oluşturabilir, kayıt altına alınır ve gerekirse yetkili makamlara bildirilir. İyi niyetli güvenlik bulguları için Güvenlik Politikası sayfamızdaki sorumlu ifşa kanalını kullanın; ücretli bir ödül programımız yoktur. Kurallara uyulmaması hesabın askıya alınmasına yol açabilir.",
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
    updated: "Last updated: August 2026",
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
          "You may not use the service for unlawful purposes, for automated abuse (including systematic attempts to bypass rate limits), or in ways that infringe the rights of others. Without our written permission you may not perform penetration testing, vulnerability scanning, password guessing (brute force), actions on behalf of someone else's email address or account, or automated crawling against the system; such actions may constitute an offence under Articles 243 and 244 of the Turkish Penal Code, are logged, and may be reported to the authorities. For good-faith security findings use the responsible disclosure channel on our Security Policy page; we do not run a paid bug bounty program. Violations may lead to account suspension.",
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

// Güvenlik politikası / sorumlu ifşa (12 Eyl 2026 güvenlik turu). Bir "güvenlik
// araştırmacısı" prod'da izinsiz test yapıp (brute force, başkası adına
// abonelik) bulgularını ücret karşılığı "teslim etmek" için mail attı. Bu sayfa
// + /.well-known/security.txt: (1) iyi niyetli bulgular için tek kanalı
// tanımlar, (2) ödül programı olmadığını açıkça söyler, (3) izinsiz testin
// yasak ve loglandığını belirtir — hem caydırıcı hem gerekirse kanıt.
export const SECURITY_POLICY: Record<Lang, LegalPage> = {
  TR: {
    title: "Güvenlik Politikası ve Sorumlu İfşa",
    updated: "Son güncelleme: Eylül 2026",
    disclaimer:
      "⚠ Bu sayfa bir başlangıç şablonudur — bağlayıcı bir hukuki belge değildir ve bir hukuk danışmanı tarafından incelenmelidir. Yine de burada yazan kurallar Kullanım Şartları'nın parçasıdır.",
    sections: [
      {
        heading: "Kapsam",
        body:
          "Bu politika nexstreamnews.com ve alt alan adları ile /api altındaki uygulama arayüzünü kapsar. Kullandığımız üçüncü taraf hizmetler (Cloudflare, Groq, Resend, Stripe, AWS) kapsam dışıdır; onlarla ilgili bulgular doğrudan ilgili sağlayıcıya bildirilmelidir.",
      },
      {
        heading: "İzinsiz test yasaktır",
        body:
          "Yazılı iznimiz olmadan sistem üzerinde sızma testi, zafiyet taraması, otomatik tarayıcı çalıştırma, parola deneme (brute force), rate limit'leri aşmaya yönelik sistematik istekler, başkasının e-posta adresi ya da hesabı adına işlem yapma, üçüncü kişilere ait verilere erişme veya hizmeti yavaşlatma/durdurma girişimleri yasaktır. Bu eylemler Kullanım Şartları'nı ihlal eder, Türk Ceza Kanunu'nun 243 (bilişim sistemine girme) ve 244 (sistemi engelleme, bozma, verileri yok etme veya değiştirme) maddeleri kapsamında suç oluşturabilir. Tüm istekler IP adresi ve zaman damgasıyla kayıt altına alınır; gerekirse yetkili makamlara iletilir.",
      },
      {
        heading: "İyi niyetli bulguları nasıl bildirirsiniz?",
        body:
          "Kendi hesabınızı ve kendi verilerinizi kullanırken fark ettiğiniz bir güvenlik sorununu, sistemde herhangi bir değişiklik yapmadan ve başka kullanıcıların verisine erişmeden, iletişim sayfamızdaki form üzerinden (kategori: Genel) bildirebilirsiniz. Makine tarafından okunabilir kanal /.well-known/security.txt adresindedir. İyi bir rapor etkilenen uç noktayı, tekrar adımlarını ve olası etkiyi içerir; 'detaylar görüşmede' tarzı içeriksiz bildirimler değerlendirilmez.",
      },
      {
        heading: "Ödül programı yoktur",
        body:
          "NexStream gönüllü olarak geliştirilen, gelir amacı gütmeyen bir portfolyo projesidir. Ücretli bir bug bounty programı yürütmüyoruz; rapor, danışmanlık ya da 'teslim süreci' karşılığında ödeme yapılmaz ve bu yöndeki talepler yanıtlanmaz. Doğrulanan iyi niyetli bulgular için, dilerseniz, bu sayfada isminizle teşekkür edilir.",
      },
      {
        heading: "Ne beklemelisiniz?",
        body:
          "Bildirimler makul bir sürede (hedef: 7 iş günü) değerlendirilir, doğrulanan bulgular düzeltilir ve size geri bildirim verilir. Bulguyu kamuya açıklamadan önce bize düzeltme için en az 90 gün tanımanızı rica ederiz. Bu politikanın sınırları içinde kalan, zarar vermeyen ve iyi niyetli bildirimler için hukuki yollara başvurmayız.",
      },
    ],
  },
  EN: {
    title: "Security Policy and Responsible Disclosure",
    updated: "Last updated: September 2026",
    disclaimer:
      "⚠ This page is a starter template — it is not a binding legal document and should be reviewed by legal counsel. The rules below are nevertheless part of the Terms of Service.",
    sections: [
      {
        heading: "Scope",
        body:
          "This policy covers nexstreamnews.com, its subdomains and the application interface under /api. Third-party services we rely on (Cloudflare, Groq, Resend, Stripe, AWS) are out of scope; findings about them must be reported directly to the respective provider.",
      },
      {
        heading: "Unauthorized testing is prohibited",
        body:
          "Without our written permission you may not perform penetration testing, vulnerability scanning, automated scanner runs, password guessing (brute force), systematic requests intended to bypass rate limits, actions on behalf of someone else's email address or account, access to other users' data, or attempts to slow down or disrupt the service. Such actions violate the Terms of Service and may constitute an offence under Articles 243 (unauthorized access to an information system) and 244 (obstructing, corrupting, destroying or altering a system or its data) of the Turkish Penal Code. All requests are logged with IP address and timestamp and may be handed to the authorities.",
      },
      {
        heading: "How to report a good-faith finding",
        body:
          "If, while using your own account and your own data, you notice a security issue, report it through the form on our contact page (category: General) without modifying anything in the system or accessing other users' data. The machine-readable channel is /.well-known/security.txt. A useful report names the affected endpoint, the steps to reproduce and the likely impact; content-free notices of the 'details in a call' kind are not evaluated.",
      },
      {
        heading: "There is no bounty program",
        body:
          "NexStream is a volunteer-built, non-commercial portfolio project. We do not run a paid bug bounty program; no payment is made for reports, consulting or a 'delivery process', and requests of that kind will not be answered. Verified good-faith findings can, if you wish, be acknowledged with your name on this page.",
      },
      {
        heading: "What to expect",
        body:
          "Reports are reviewed within a reasonable time (target: 7 business days), verified findings are fixed and you receive feedback. We ask that you give us at least 90 days to fix an issue before disclosing it publicly. We will not pursue legal action for good-faith, non-damaging reports that stay within the limits of this policy.",
      },
    ],
  },
};
