import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

from .models import ChatMessage


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_group_name = 'test'
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()
        messages = list(
            ChatMessage.objects.order_by('-created_at', '-pk').values(
                'id', 'message', 'created_at'
            )[:100]
        )
        messages.reverse()
        self.send(text_data=json.dumps({
            'type': 'history',
            'messages': [
                {
                    **message,
                    'created_at': message['created_at'].isoformat(),
                }
                for message in messages
            ],
        }))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            self.send(text_data=json.dumps({'type': 'pong'}))
            return

        message = data.get('message', '').strip()
        if not message:
            return
        if len(message) > 2000:
            self.close(code=1009)
            return

        chat_message = ChatMessage.objects.create(message=message)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': chat_message.pk,
                'message': chat_message.message,
                'created_at': chat_message.created_at.isoformat(),
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps({
            'type': 'chat',
            'id': event['id'],
            'message': event['message'],
            'created_at': event['created_at'],
        }))
