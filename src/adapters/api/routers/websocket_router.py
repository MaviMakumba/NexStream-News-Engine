import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from src.adapters.notifications.websocket_notifier import WebSocketNotifier
from src.dependencies import get_notifier

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket, notifier: WebSocketNotifier = Depends(get_notifier)):
    """
    Canlı haber akışı. Bağlantı kurulunca mevcut son haberler gönderilir,
    ardından her yeni haber DB poller aracılığıyla push edilir.
    """
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
