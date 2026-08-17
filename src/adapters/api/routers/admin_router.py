"""Admin endpoint'leri (/admin) — kullanım istatistikleri, kullanıcı/rol yönetimi + sponsor CRUD.

Yetkilendirme (v1.13, iki seviyeli; rol değiştirme v2.1'de kademeliye geçti):
    require_moderator — router genelinde: hem GÖRÜNTÜLEME (kullanım/kullanıcı/
        sponsor listeleri) hem de rol değiştirme (`PATCH /users/{id}/role`)
        için giriş kapısı. X-API-Key VEYA moderator/admin/owner rolündeki
        kullanıcı oturumu. Rol değiştirmede asıl yetki sınırlaması route
        düzeyinde DEĞİL, handler içindeki rank-comparison (`role_at_least`)
        mantığıyla uygulanır — bkz. `update_user_role` docstring'i.
    require_admin — YAZMA işlemleri (sponsor CRUD) route düzeyinde ayrıca
        ister. X-API-Key VEYA role="admin" (veya ADMIN_EMAILS'teki).

Sponsor yönetimi kasıtlı olarak basit tutuldu (tek tablo, soft-delete):
silme yerine `is_active=false` yazılır ki geçmiş kampanyalar raporlanabilsin.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.adapters.api.auth_utils import require_admin, require_moderator, get_current_user, effective_role
from src.adapters.repositories.user_repository import UserRepository
from src.adapters.repositories.orm_models import SponsorORM
from src.domain.models.sponsor import Sponsor
from src.domain.models.user import User, UserRole, role_at_least
from src.infrastructure.config.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_moderator)])


# ── Kullanım istatistikleri ────────────────────────────────────────────────────

@router.get("/usage")
def get_usage_stats(
    user_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Endpoint bazında istek sayısı/ortalama gecikme — opsiyonel kullanıcı filtresi."""
    repo = UserRepository(db)
    return repo.get_usage_stats(user_id=user_id, days=days)


# ── Müşteri/kullanıcı listesi ───────────────────────────────────────────────────

@router.get("/users")
def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tier: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Kayıtlı tüm kullanıcılar — tier, aktiflik ve gerçek ödeme durumu.

    `is_paying`, `stripe_customer_id`'nin dolu olup olmadığından türetilir:
    BILLING_DEV_MODE'daki tek-tık tier yükseltmeleri bu alanı hiç YAZMAZ
    (bkz. billing_router.py), sadece gerçek Stripe checkout/webhook yazar —
    yani bu alan "dev-mode'da yükseltilmiş" ile "gerçekten ödeyen" ayrımını verir.
    """
    repo = UserRepository(db)
    users = repo.list_users(limit=limit, offset=offset, tier=tier)
    return {
        "total": repo.count_users(tier=tier),
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "tier": u.tier.value if hasattr(u.tier, "value") else u.tier,
                "is_active": u.is_active,
                "role": effective_role(u),
                "is_paying": bool(u.stripe_customer_id),
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


class RoleUpdateRequest(BaseModel):
    role: str


_ASSIGNABLE_ROLES = (UserRole.USER.value, UserRole.MODERATOR.value, UserRole.ADMIN.value)


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    req: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Başka bir kullanıcının rolünü değiştirir — kademeli yetki (v2.1).

    Kurallar: (1) owner rolü asla atanamaz — tek kaynak OWNER_EMAILS env;
    (2) kimse kendi rolünü kendisi değiştiremez; (3) hedefin mevcut rolü
    istek sahibinden KESİNLİKLE düşük olmalı (eşit/üst roldekine dokunulamaz);
    (4) atanacak yeni rol istek sahibinin rolünü AŞAMAZ. Owner herkesi
    yönetir, kendisine kimse dokunamaz (rank'i herkesten yüksek olduğu için
    kural 3 otomatik sağlanır).
    """
    if req.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="role must be user, moderator or admin")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Kendi rolünüzü kendiniz değiştiremezsiniz.")

    repo = UserRepository(db)
    target = repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    actor_role = effective_role(current_user)
    target_role = effective_role(target)
    # Hedefin rolü actor'dan KESİNLİKLE düşük olmalı — role_at_least(target, actor)
    # true ise hedef actor'a eşit/üst demektir, izin verilmez.
    if role_at_least(target_role, actor_role):
        raise HTTPException(status_code=403, detail="Bu kullanıcının rolünü değiştirme yetkiniz yok")
    # Atanacak rol actor'un rolünü aşamaz — role_at_least(actor, new_role) false ise reddedilir.
    if not role_at_least(actor_role, req.role):
        raise HTTPException(status_code=403, detail="Bu kullanıcının rolünü değiştirme yetkiniz yok")

    if not repo.update_role(user_id, req.role):
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("Rol değişti: user_id=%s → %s (işlemi yapan: %s)", user_id, req.role, current_user.email)
    return {"id": user_id, "role": req.role}


# ── Sponsor CRUD ───────────────────────────────────────────────────────────────

class SponsorRequest(BaseModel):
    name: str
    url: str
    message: str
    active_from: datetime
    active_until: datetime


def _to_dict(orm: SponsorORM) -> dict:
    return {
        "id": orm.id,
        "name": orm.name,
        "url": orm.url,
        "message": orm.message,
        "active_from": orm.active_from,
        "active_until": orm.active_until,
        "is_active": orm.is_active,
    }


@router.get("/sponsors")
def list_sponsors(db: Session = Depends(get_db)):
    rows = db.query(SponsorORM).order_by(text("active_from DESC")).all()
    return [_to_dict(r) for r in rows]


def _deactivate_all_active_sponsors(db: Session) -> None:
    """Tek "güncel sponsor" değişmezini korur (newsletter footer'ı ve admin
    panelindeki "aktif sponsor" kartı ikisi de tekil bir kayıt bekler) — yoksa
    birden fazla is_active=true kayıt oluşur ve arayüz sadece ilkini gösterip
    diğerlerini sessizce gizler."""
    db.query(SponsorORM).filter(SponsorORM.is_active.is_(True)).update({"is_active": False})


@router.post("/sponsors", status_code=201, dependencies=[Depends(require_admin)])
def create_sponsor(req: SponsorRequest, db: Session = Depends(get_db)):
    _deactivate_all_active_sponsors(db)
    orm = SponsorORM(
        name=req.name,
        url=req.url,
        message=req.message,
        active_from=req.active_from,
        active_until=req.active_until,
        is_active=True,
    )
    db.add(orm)
    db.commit()
    db.refresh(orm)
    logger.info("Yeni sponsor: %s", req.name)
    # Yanıt req'ten kurulur: testlerdeki mock session'larda ORM lazy-load tetiklenmesin
    return {
        "id": getattr(orm, "id", None),
        "name": req.name,
        "url": req.url,
        "message": req.message,
        "active_from": req.active_from,
        "active_until": req.active_until,
        "is_active": True,
    }


@router.patch("/sponsors/{sponsor_id}", dependencies=[Depends(require_admin)])
def update_sponsor(sponsor_id: int, req: SponsorRequest, db: Session = Depends(get_db)):
    orm = db.get(SponsorORM, sponsor_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    orm.name = req.name
    orm.url = req.url
    orm.message = req.message
    orm.active_from = req.active_from
    orm.active_until = req.active_until
    db.commit()
    return _to_dict(orm)


@router.delete("/sponsors/{sponsor_id}", dependencies=[Depends(require_admin)])
def deactivate_sponsor(sponsor_id: int, db: Session = Depends(get_db)):
    """Soft-delete: kayıt silinmez, sadece pasife alınır."""
    orm = db.get(SponsorORM, sponsor_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    orm.is_active = False
    db.commit()
    return {"id": sponsor_id, "is_active": False}


@router.delete("/sponsors/{sponsor_id}/permanent", dependencies=[Depends(require_admin)])
def delete_sponsor_permanently(sponsor_id: int, db: Session = Depends(get_db)):
    """Kaydı kalıcı olarak siler — geri alınamaz. Süresi dolmuş/pasif eski
    kayıtları listeden tamamen temizlemek için (soft-delete'in aksine)."""
    orm = db.get(SponsorORM, sponsor_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    db.delete(orm)
    db.commit()
    return {"id": sponsor_id, "deleted": True}


@router.post("/sponsors/{sponsor_id}/activate", dependencies=[Depends(require_admin)])
def activate_sponsor(sponsor_id: int, db: Session = Depends(get_db)):
    """Süresi geçmemiş pasif bir sponsoru yeniden aktifleştirir — diğer
    aktif sponsor(lar) otomatik pasife alınır (tek güncel sponsor kuralı)."""
    orm = db.get(SponsorORM, sponsor_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    _deactivate_all_active_sponsors(db)
    orm.is_active = True
    db.commit()
    return _to_dict(orm)


def get_active_sponsor(db: Session) -> Optional[Sponsor]:
    """Şu an yayında olan sponsoru döner (newsletter footer'ında kullanılır)."""
    now = datetime.now(timezone.utc)
    orm = (
        db.query(SponsorORM)
        .filter(
            SponsorORM.is_active.is_(True),
            SponsorORM.active_from <= now,
            SponsorORM.active_until >= now,
        )
        .first()
    )
    if not orm:
        return None
    return Sponsor(
        id=orm.id,
        name=orm.name,
        url=orm.url,
        message=orm.message,
        active_from=orm.active_from,
        active_until=orm.active_until,
        is_active=orm.is_active,
    )
