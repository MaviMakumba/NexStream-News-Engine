"""Kullanıcı API anahtarı saklama biçimi (12 Eylül 2026 güvenlik turu).

`users.api_key` düz metin saklanıyordu — DB sızıntısında/yedek dosyasında tüm
anahtarlar doğrudan kullanılabilir olurdu. Anahtar rastgele 24 byte
(`secrets.token_urlsafe`) olduğu için bcrypt gibi yavaş bir hash gereksiz;
SHA-256 yeterli ve kolon (String(64)) tam hex uzunluğunda. Ham anahtar sadece
üretildiği yanıtta görünür, bir daha okunamaz.
"""

import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.database import Base
from src.adapters.repositories.user_repository import UserRepository, hash_api_key
from src.adapters.repositories.orm_models import UserORM


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _user(db):
    row = UserORM(email="k@test.com", password_hash="h")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_hash_api_key_is_sha256_hex():
    assert hash_api_key("nxs_abc") == hashlib.sha256(b"nxs_abc").hexdigest()
    assert len(hash_api_key("nxs_abc")) == 64


def test_set_api_key_stores_hash_not_raw_key():
    db = _session()
    row = _user(db)
    UserRepository(db).set_api_key(row.id, "nxs_raw-secret")
    db.refresh(row)
    assert row.api_key != "nxs_raw-secret"
    assert row.api_key == hash_api_key("nxs_raw-secret")


def test_get_by_api_key_resolves_raw_key():
    db = _session()
    row = _user(db)
    repo = UserRepository(db)
    repo.set_api_key(row.id, "nxs_raw-secret")
    found = repo.get_by_api_key("nxs_raw-secret")
    assert found is not None and found.id == row.id


def test_get_by_api_key_rejects_stored_hash_as_credential():
    """DB'den sızan hash'in kendisi anahtar olarak KULLANILAMAMALI."""
    db = _session()
    row = _user(db)
    repo = UserRepository(db)
    repo.set_api_key(row.id, "nxs_raw-secret")
    assert repo.get_by_api_key(hash_api_key("nxs_raw-secret")) is None


def test_set_api_key_none_revokes():
    db = _session()
    row = _user(db)
    repo = UserRepository(db)
    repo.set_api_key(row.id, "nxs_raw-secret")
    repo.set_api_key(row.id, None)
    db.refresh(row)
    assert row.api_key is None
    assert repo.get_by_api_key("nxs_raw-secret") is None
