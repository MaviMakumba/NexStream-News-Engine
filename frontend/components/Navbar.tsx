"use client";

// Navbar, giriş durumuna göre farklı içerik render eder (Giriş Yap/Kayıt Ol
// vs. kullanıcı adı). SSR sunucu localStorage'ı bilemediği için gerçek
// implementasyon (NavbarImpl) sadece client'ta mount edilir — bu sayede
// "önce misafir görünüp sonra giriş yapmış hale geçme" flaş'ı (FOUC) hiç
// oluşmaz: yanlış bir hal render edilmez, sadece bir an boş yer tutucu
// gösterilir, ardından mount olduğunda DOĞRUDAN doğru durumla belirir.
import dynamic from "next/dynamic";

const NavbarPlaceholder = () => (
  <div style={{
    height: 56,
    borderBottom: "1px solid var(--border)",
    background: "var(--surface)",
    position: "sticky", top: 0, zIndex: 40,
  }} />
);

export const Navbar = dynamic(() => import("./NavbarImpl").then((m) => m.Navbar), {
  ssr: false,
  loading: NavbarPlaceholder,
});
