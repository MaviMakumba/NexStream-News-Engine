import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://nexstream.news";

// Giriş/kayıt sayfaları bilinçli olarak YOK: ince, odaklı ekranlar — dizine
// girmeleri değer katmıyor, "kopya/ince sayfa" uyarısı riski taşıyor.
// Not: haber detayları için ayrı SSR sayfası yok (içerik sadece arama/liste
// API'leri üzerinden erişilebilir) — bu yüzden dinamik/haber-bazlı bir sitemap
// üretilemiyor. Sadece gerçek statik public rotalar listelenir.
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/security`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/contact`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
  ];
}
