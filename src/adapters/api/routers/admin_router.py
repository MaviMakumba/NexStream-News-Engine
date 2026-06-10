"""Admin endpoint'leri (/admin) — kullanım istatistikleri + sponsor CRUD.

Yetkilendirme (v1.11, `require_admin`): iki yoldan biri yeterlidir.
    1. X-API-Key       — paylaşımlı makine-makine anahtarı (script/CI için)
    2. X-Session-Token — `is_admin=true` olan (veya ADMIN_EMAILS'teki) kullanıcı

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

from src.adapters.api.auth_utils import require_admin
from src.adapters.repositories.user_repository import UserRepository
from src.adapters.repositories.orm_models import SponsorORM
from src.domain.models.sponsor import Sponsor
from src.infrastructure.config.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


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


@router.post("/sponsors", status_code=201)
def create_sponsor(req: SponsorRequest, db: Session = Depends(get_db)):
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


@router.patch("/sponsors/{sponsor_id}")
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


@router.delete("/sponsors/{sponsor_id}")
def deactivate_sponsor(sponsor_id: int, db: Session = Depends(get_db)):
    """Soft-delete: kayıt silinmez, sadece pasife alınır."""
    orm = db.get(SponsorORM, sponsor_id)
    if not orm:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    orm.is_active = False
    db.commit()
    return {"id": sponsor_id, "is_active": False}


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
