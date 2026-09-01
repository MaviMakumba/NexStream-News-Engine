"""Public OpenAPI şeması (/docs, /openapi.json) neyi göstermeli testleri.

1 Eyl 2026'da kullanıcı fark etti: /docs kimlik doğrulaması gerektirmeden
HERKESE açık (main.py'de docs_url kapatılmamış, bilinçli — self-serve
/api/v1 geliştirici portalı için). Ama /admin/* uçları da (rol/tier
değiştirme, sponsor CRUD) aynı public şemada tam path+schema detayıyla
görünüyordu — çağrı hâlâ require_moderator/require_admin/require_owner ile
korunuyor (bkz. test_admin_router.py), yani bu bir yetkisiz erişim AÇIĞI
DEĞİL, ama admin API yüzeyinin tamamını (hangi path'ler var, hangi alanları
kabul ediyor) anonim bir ziyaretçiye Swagger'ın "Try it out" formuyla
sunmak gereksiz keşif kolaylığı sağlıyordu. Düzeltme: admin_router'a
include_in_schema=False — davranış (auth/routing) DEĞİŞMİYOR, sadece
dokümantasyon görünürlüğü kapanıyor.
"""


def test_admin_paths_hidden_from_public_openapi_schema(app_client):
    """/admin/* uçları public OpenAPI şemasında (dolayısıyla /docs'ta) görünmemeli."""
    resp = app_client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    admin_paths = [p for p in paths if p.startswith("/admin")]
    assert admin_paths == [], f"Admin path'leri hâlâ public şemada görünüyor: {admin_paths}"


def test_normal_endpoints_still_visible_in_openapi_schema(app_client):
    """Sadece admin gizlendi — normal/public uçlar şemadan kaybolmamalı."""
    resp = app_client.get("/openapi.json")
    paths = resp.json()["paths"]
    assert "/news/search" in paths
    assert "/feed.xml" in paths
