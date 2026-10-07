"""SSRF koruması — makale URL'leri kendi RSS'imizden gelir ama kötü niyetli/ele geçirilmiş bir
feed (ya da Hacker News gibi keyfi sitelere link veren bir kaynak) iç ağı hedefleyemesin.

Bilinen sınır: DNS çözümü ile gerçek bağlantı arasında TOCTOU (DNS rebinding) penceresi var;
HTTPS'te IP'ye sabitlemek SNI/sertifika doğrulamasını karmaşıklaştırdığı için ilk sürümde
kabul edildi. Çıkış yalnız GET + yalnız HTML okuma + cevap kullanıcıya ham dönmediği için
etkisi sınırlı (metin yalnız LLM bağlamına girer).
"""

import ipaddress
import socket
from urllib.parse import urlsplit

_ALLOWED_PORTS = {80, 443}


class UnsafeUrlError(ValueError):
    """URL fetch edilmemeli (şema, port ya da çözülen adres güvensiz)."""


_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _embedded_ipv4(ip):
    """IPv6 içine gömülmüş IPv4'ü (mapped ::ffff:a.b.c.d, uyumlu ::a.b.c.d, NAT64 64:ff9b::/96)
    açar: bu biçimler yanlış `is_global=True` dönebilir, asıl hedef gömülü IPv4'tür."""
    if ip.version != 6:
        return ip
    if ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    if int(ip) >> 32 == 0 or ip in _NAT64:
        return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip


def assert_public_http_url(url: str, resolver=socket.getaddrinfo) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"izin verilmeyen şema: {parts.scheme!r}")
    host = parts.hostname
    if not host:
        raise UnsafeUrlError("host yok")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as e:
        raise UnsafeUrlError("geçersiz port") from e
    if port not in _ALLOWED_PORTS:
        raise UnsafeUrlError(f"izin verilmeyen port: {port}")
    try:
        infos = resolver(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UnsafeUrlError(f"DNS çözülemedi: {host}") from e
    if not infos:
        raise UnsafeUrlError(f"adres bulunamadı: {host}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        ip = _embedded_ipv4(ip)
        if not ip.is_global:
            raise UnsafeUrlError(f"global olmayan adres: {ip}")
