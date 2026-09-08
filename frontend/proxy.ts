/**
 * İstek başına rastgele bir CSP nonce'u üretir — `script-src`'den 'unsafe-inline'
 * VE 'unsafe-eval'i gerçek anlamda kaldırmanın tek yolu bu (bkz. nginx.conf'taki
 * eski yorum: "nonce'a geçiş ayrı bir iş").
 *
 * nginx.conf'taki CSP header'ına (statik, /api/docs Swagger UI dahil TÜM
 * location'lara uygulanıyor — o yüzden orada 'unsafe-inline'/cdn.jsdelivr.net
 * hâlâ duruyor, DOKUNULMADI) EK OLARAK gönderiliyor, onun YERİNE değil. Tarayıcı
 * birden fazla Content-Security-Policy header'ını KESİŞİM (AND) olarak uygular —
 * yani nonce'suz enjekte edilmiş bir script nginx'in gevşek policy'sinden geçse
 * bile bu policy'de bloklanır. Böylece nginx.conf'a hiç dokunmadan (Swagger UI'ı
 * kırma riski sıfır) sadece Next.js'in kendi ürettiği sayfalar için daha sıkı
 * bir ikinci katman ekliyoruz.
 *
 * 'strict-dynamic': nonce'lu bir script çalıştırdığında, o script'in DOM'a
 * enjekte ettiği diğer script'ler (Next.js'in kendi chunk-loading mekanizması)
 * otomatik güvenilir sayılır — tek tek nonce basmaya gerek kalmaz.
 * 'unsafe-inline' fallback olarak listede duruyor ama zararsız: CSP spesifikasyonu
 * gereği nonce-source/strict-dynamic içeren bir policy'de modern tarayıcılar
 * 'unsafe-inline'ı YOK SAYAR — sadece nonce/strict-dynamic'i anlamayan çok eski
 * tarayıcılar için zarif bir geri düşüş (graceful degradation).
 */
import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");

  const cspHeader = `
    script-src 'self' 'nonce-${nonce}' 'strict-dynamic' 'unsafe-inline' https://cdn.jsdelivr.net;
  `
    .replace(/\s{2,}/g, " ")
    .trim();

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", cspHeader);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", cspHeader);
  return response;
}

export const config = {
  matcher: [
    // _next/static, _next/image, favicon ve statik dosya uzantıları hariç her
    // şey — nonce'un anlamı olmadığı yerlerde middleware'i çalıştırmaya gerek yok.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|xml|txt|json|webmanifest)$).*)",
  ],
};
