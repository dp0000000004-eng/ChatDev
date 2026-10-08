from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from .consumers import ChatConsumer
from .models import ChatMessage


class ChatMessagePersistenceTests(TransactionTestCase):
    def test_websocket_messages_are_saved_and_shown_in_chat_history(self):
        async def send_message():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to({'message': '  Hello, group!  '})
            response = await communicator.receive_json_from()
            await communicator.disconnect()
            return response

        response = async_to_sync(send_message)()

        self.assertEqual(response['type'], 'chat')
        self.assertEqual(response['message'], 'Hello, group!')
        saved_message = ChatMessage.objects.get()
        self.assertEqual(saved_message.message, 'Hello, group!')

        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['chat_messages'][0]['message'], 'Hello, group!')
