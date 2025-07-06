from fastapi import WebSocket, WebSocketDisconnect
from fastapi import APIRouter
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Map user_id to WebSocket connection
        self.active_connections: dict[str, WebSocket] = {}
        # Map user_id to user role for notification targeting
        self.user_roles: dict[str, str] = {}
        # Map user_id to user email for better notifications
        self.user_emails: dict[str, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str, user_role: str = None, user_email: str = None):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        if user_role:
            self.user_roles[user_id] = user_role
        if user_email:
            self.user_emails[user_id] = user_email
        logger.info(f"Client connected: {user_id} (role: {user_role}, email: {user_email}) - Total connections: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_roles:
            del self.user_roles[user_id]
        if user_id in self.user_emails:
            del self.user_emails[user_id]
        logger.info(f"Client disconnected: {user_id} - Total connections: {len(self.active_connections)}")

    async def send_json_by_user_id(self, message: dict, user_id: str):
        """Send JSON message to specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                logger.info(f"Sent notification to user {user_id}: {message}")
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                # Remove stale connection
                self.disconnect(user_id)

    async def notify_maintainers_and_admins(self, message: dict):
        """Notify all MAINTAINER and ADMIN users"""
        logger.info(f"Notifying maintainers and admins: {message}")
        notified_count = 0
        for user_id, role in self.user_roles.items():
            if role in ['MAINTAINER', 'ADMIN']:
                await self.send_json_by_user_id(message, user_id)
                notified_count += 1
        logger.info(f"Notified {notified_count} maintainers/admins")

    async def notify_reporter(self, message: dict, reporter_id: str):
        """Notify specific reporter about their issue"""
        logger.info(f"Notifying reporter {reporter_id}: {message}")
        if reporter_id in self.active_connections:
            await self.send_json_by_user_id(message, reporter_id)
            logger.info(f"Successfully notified reporter {reporter_id}")
        else:
            logger.info(f"Reporter {reporter_id} not connected")

    async def notify_all_users(self, message: dict):
        """Broadcast message to all connected users"""
        logger.info(f"Notifying all users: {message}")
        notified_count = 0
        for user_id in list(self.active_connections.keys()):
            await self.send_json_by_user_id(message, user_id)
            notified_count += 1
        logger.info(f"Notified {notified_count} users")

    async def notify_issue_participants(self, message: dict, issue_reporter_id: str, exclude_user_id: str = None):
        """Notify all relevant users about an issue change"""
        # Notify the reporter (if different from the one making the change)
        if exclude_user_id != issue_reporter_id:
            await self.notify_reporter(message, issue_reporter_id)
        
        # Notify all maintainers and admins (except the one making the change)
        for user_id, role in self.user_roles.items():
            if role in ['MAINTAINER', 'ADMIN'] and user_id != exclude_user_id:
                await self.send_json_by_user_id(message, user_id)

    def get_connected_users_info(self):
        """Get info about all connected users for debugging"""
        return {
            user_id: {
                'role': self.user_roles.get(user_id),
                'email': self.user_emails.get(user_id),
                'connected': True
            }
            for user_id in self.active_connections.keys()
        }

manager = ConnectionManager()

@router.websocket("/notification")
async def websocket_endpoint(websocket: WebSocket):
    user_id = websocket.query_params.get("userid")
    user_role = websocket.query_params.get("role")
    user_email = websocket.query_params.get("email")
    
    if not user_id:
        await websocket.close()
        return

    await manager.connect(websocket, user_id, user_role, user_email)
    
    try:
        while True:
            # Keep connection alive with ping/pong
            data = await websocket.receive_text()
            # Optional: handle any client messages here
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)
