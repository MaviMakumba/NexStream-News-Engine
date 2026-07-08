import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://nexstream.news";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/dashboard",
          "/account",
          "/admin",
          "/auth/forgot-password",
          "/auth/reset-password",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
