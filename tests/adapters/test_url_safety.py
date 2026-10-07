import socket

import pytest

from src.adapters.scrapers.url_safety import UnsafeUrlError, assert_public_http_url


def _resolver(*ips):
    def resolve(host, port, type=socket.SOCK_STREAM):
        return [(socket.AF_INET, type, 6, "", (ip, port)) for ip in ips]
    return resolve


def test_public_https_url_passes():
    assert_public_http_url("https://example.com/haber/1", resolver=_resolver("93.184.216.34"))


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "gopher://example.com/",
    "javascript:alert(1)",
    "//example.com/x",
    "https:///nohost",
])
def test_non_http_or_hostless_urls_rejected(url):
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url(url, resolver=_resolver("93.184.216.34"))


@pytest.mark.parametrize("ip", [
    "127.0.0.1", "10.0.0.5", "172.16.3.4", "192.168.1.1",
    "169.254.169.254", "100.64.0.1", "0.0.0.0", "::1", "fe80::1", "::ffff:127.0.0.1", "fc00::1",
])
def test_non_global_addresses_rejected(ip):
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://evil.example/x", resolver=_resolver(ip))


def test_rejected_if_any_resolved_address_is_private():
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://mixed.example/", resolver=_resolver("93.184.216.34", "10.0.0.1"))


def test_unresolvable_host_and_empty_resolution_rejected():
    def boom(host, port, type=socket.SOCK_STREAM):
        raise socket.gaierror("nope")
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://nxdomain.example/", resolver=boom)
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url("https://empty.example/", resolver=lambda h, p, type=0: [])


@pytest.mark.parametrize("url", ["https://example.com:8080/x", "http://example.com:22/"])
def test_non_web_ports_rejected(url):
    with pytest.raises(UnsafeUrlError):
        assert_public_http_url(url, resolver=_resolver("93.184.216.34"))


def test_explicit_standard_ports_allowed():
    assert_public_http_url("http://example.com:80/x", resolver=_resolver("93.184.216.34"))
    assert_public_http_url("https://example.com:443/x", resolver=_resolver("93.184.216.34"))
