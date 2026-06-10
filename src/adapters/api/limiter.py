"""slowapi rate limiter singleton'ı — tüm router'lar bu instance'ı paylaşır."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
