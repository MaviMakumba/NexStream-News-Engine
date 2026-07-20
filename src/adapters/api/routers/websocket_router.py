"""WebSocket canlı akış endpoint'i (/ws/feed).

Yeni haberler main.py'deki DB poller'ı üzerinden push edilir; 30sn sessizlikte
sunucu ping atarak bağlantıyı canlı tutar.
"""

import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from src.adapters.notifications.websocket_notifier import WebSocketNotifier
from src.adapters.api.auth_utils import get_optional_user
from src.domain.models.user import User, UserTier, tier_at_least
from src.dependencies import get_notifier

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/feed")
async def websocket_feed(
    websocket: WebSocket,
    notifier: WebSocketNotifier = Depends(get_notifier),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Canlı haber akışı — Pro+ özelliği. Bağlantı kurulunca mevcut son haberler
    gönderilir, ardından her yeni haber DB poller aracılığıyla push edilir.
    """
    if not user or not tier_at_least(user.tier, UserTier.PRO):
        # ÖNCE accept(), SONRA close(code=...) — handshake tamamlanmadan (101
        # Switching Protocols hiç dönmeden) close çağrılırsa Starlette
        # TestClient close code'u doğru taşır ama GERÇEK tarayıcılar açılış
        # handshake'i başarısız olduğu için özel kodu hiç göremez, sadece genel
        # "1006 abnormal closure" görür (frontend'in locked/retry ayrımı bozulur).
        await websocket.accept()
        await websocket.close(code=1008, reason="Pro plan required for live feed")
        return
    await notifier.connect(websocket)
    try:
        while True:
            try:
                # Client ping'ini bekle; 30sn timeout → server ping gönder
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket hatası: %s", e)
    finally:
        notifier.disconnect(websocket)
