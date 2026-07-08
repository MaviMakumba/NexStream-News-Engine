import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://nexstream.news";

// Not: haber detayları için ayrı SSR sayfası yok (içerik sadece arama/liste
// API'leri üzerinden erişilebilir) — bu yüzden dinamik/haber-bazlı bir sitemap
// üretilemiyor. Sadece gerçek statik public rotalar listelenir.
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: `${SITE_URL}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/auth/login`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/auth/register`, lastModified: now, changeFrequency: "yearly", priority: 0.5 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
  ];
}
