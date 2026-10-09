from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from .consumers import ChatConsumer
from .models import ChatMessage


class ChatMessagePersistenceTests(TransactionTestCase):
    def test_websocket_heartbeat_returns_pong_without_saving_message(self):
        async def check_heartbeat():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            history = await communicator.receive_json_from()
            await communicator.send_json_to({'type': 'ping'})
            response = await communicator.receive_json_from()
            await communicator.disconnect()
            return history, response

        history, response = async_to_sync(check_heartbeat)()

        self.assertEqual(history, {'type': 'history', 'messages': []})
        self.assertEqual(response, {'type': 'pong'})
        self.assertFalse(ChatMessage.objects.exists())

    def test_websocket_reconnect_receives_saved_history(self):
        saved_message = ChatMessage.objects.create(message='While you were away')

        async def load_history():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            history = await communicator.receive_json_from()
            await communicator.disconnect()
            return history

        history = async_to_sync(load_history)()

        self.assertEqual(history['type'], 'history')
        self.assertEqual(history['messages'], [{
            'id': saved_message.pk,
            'message': 'While you were away',
            'created_at': saved_message.created_at.isoformat(),
        }])

    def test_websocket_messages_are_saved_and_shown_in_chat_history(self):
        async def send_message():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            await communicator.send_json_to({'message': '  Hello, group!  '})
            response = await communicator.receive_json_from()
            await communicator.disconnect()
            return response

        response = async_to_sync(send_message)()

        self.assertEqual(response['type'], 'chat')
        self.assertEqual(response['message'], 'Hello, group!')
        saved_message = ChatMessage.objects.get()
        self.assertEqual(saved_message.message, 'Hello, group!')
        self.assertEqual(response['id'], saved_message.pk)

        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['chat_messages'][0]['message'], 'Hello, group!')
