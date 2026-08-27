import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class WorkItemConsumer(AsyncWebsocketConsumer):
    """Real-time WebSocket consumer for work item boards, sprints, and ticket queues.
    Clients subscribe to project-specific groups to receive live updates.
    """

    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs'].get('project_id')
        self.workspace_id = self.scope['url_route']['kwargs'].get('workspace_id')

        # Authenticate via JWT query param
        self.user = await self._get_user()
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Build group names for subscription
        self.board_group = f'board_{self.project_id}' if self.project_id else None
        self.workspace_group = f'workspace_{self.workspace_id}' if self.workspace_id else None

        # Join groups
        if self.board_group:
            await self.channel_layer.group_add(self.board_group, self.channel_name)
        if self.workspace_group:
            await self.channel_layer.group_add(self.workspace_group, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if self.board_group:
            await self.channel_layer.group_discard(self.board_group, self.channel_name)
        if self.workspace_group:
            await self.channel_layer.group_discard(self.workspace_group, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming messages from the WebSocket client."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get('action')
        payload = data.get('payload', {})

        if action == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    # ── Broadcast handlers called by channel_layer.group_send ──────────

    async def board_update(self, event):
        """Broadcast board column/item changes to all viewers."""
        await self.send(text_data=json.dumps({
            'type': 'board_update',
            'project_id': event.get('project_id'),
            'column_id': event.get('column_id'),
            'item': event.get('item'),
            'action': event.get('subtype', 'updated'),
        }))

    async def sprint_update(self, event):
        """Broadcast sprint status changes."""
        await self.send(text_data=json.dumps({
            'type': 'sprint_update',
            'sprint_id': event.get('sprint_id'),
            'status': event.get('status'),
            'action': event.get('subtype', 'updated'),
        }))

    async def ticket_update(self, event):
        """Broadcast ticket queue changes (new ticket, SLA breach, status change)."""
        await self.send(text_data=json.dumps({
            'type': 'ticket_update',
            'ticket_id': event.get('ticket_id'),
            'action': event.get('subtype', 'updated'),
            'sla_status': event.get('sla_status'),
        }))

    async def workspace_summary(self, event):
        """Broadcast workspace-level summary changes."""
        await self.send(text_data=json.dumps({
            'type': 'workspace_summary',
            'workspace_id': event.get('workspace_id'),
            'summary': event.get('summary'),
        }))

    @database_sync_to_async
    def _get_user(self):
        """Authenticate user from JWT token in query string."""
        try:
            token_key = self.scope['query_string'].decode().split('token=')[-1].split('&')[0]
            access = AccessToken(token_key)
            return User.objects.get(id=access['user_id'])
        except Exception:
            return None


# ── Helper functions for broadcasting from views ──────────────────────

def notify_board_update(channel_layer, project_id, column_id=None, item=None, subtype='updated'):
    """Notify all board viewers of a change."""
    channel_layer.group_send(
        f'board_{project_id}',
        {
            'type': 'board_update',
            'project_id': str(project_id),
            'column_id': str(column_id) if column_id else None,
            'item': item,
            'subtype': subtype,
        }
    )


def notify_sprint_update(channel_layer, sprint_id, project_id, status, subtype='updated'):
    """Notify all sprint viewers of a change."""
    channel_layer.group_send(
        f'board_{project_id}',
        {
            'type': 'sprint_update',
            'sprint_id': str(sprint_id),
            'status': status,
            'subtype': subtype,
        }
    )


def notify_ticket_update(channel_layer, ticket_id, project_id, subtype='updated', sla_status=None):
    """Notify all ticket queue viewers of a change."""
    channel_layer.group_send(
        f'board_{project_id}',
        {
            'type': 'ticket_update',
            'ticket_id': str(ticket_id),
            'subtype': subtype,
            'sla_status': sla_status,
        }
    )
