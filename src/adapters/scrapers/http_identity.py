"""Dış sitelere giden tüm HTTP istemcilerinin paylaştığı tarayıcı kimliği.

Bare "Mozilla/5.0" klasik bot imzasıdır — gerçek tarayıcılar hiçbir zaman tek başına
göndermez; AA'nın WAF'ı bunu TLS seviyesinde reddediyordu (9 Eylül 2026). RSS çekicisi ve
makale metni çekicisi AYNI sabiti kullanır ki UA bir yerde güncellenip ötekinde unutulmasın.
"""

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
