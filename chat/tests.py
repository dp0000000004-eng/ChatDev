from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase

from .consumers import ChatConsumer
from .models import ChatMessage, Nickname


class ChatMessagePersistenceTests(TransactionTestCase):
    def test_websocket_heartbeat_returns_pong_without_saving_message(self):
        async def check_heartbeat():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            communicator.scope['session'] = {}
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
            communicator.scope['session'] = {}
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
            'nickname': 'Guest',
            'created_at': saved_message.created_at.isoformat(),
        }])

    def test_websocket_messages_are_saved_and_shown_in_chat_history(self):
        nickname = Nickname.objects.create(nickname='Sunny')

        async def send_message():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            communicator.scope['session'] = {'nickname_id': nickname.pk}
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
        self.assertEqual(response['nickname'], 'Sunny')
        saved_message = ChatMessage.objects.get()
        self.assertEqual(saved_message.message, 'Hello, group!')
        self.assertEqual(saved_message.name, nickname)
        self.assertEqual(response['id'], saved_message.pk)

        async def load_saved_history():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            communicator.scope['session'] = {'nickname_id': nickname.pk}
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            history = await communicator.receive_json_from()
            await communicator.disconnect()
            return history

        history = async_to_sync(load_saved_history)()
        self.assertEqual(history['messages'][0]['nickname'], 'Sunny')

        page = self.client.get('/chat/')
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['chat_messages'][0]['message'], 'Hello, group!')
        self.assertEqual(page.context['chat_messages'][0]['nickname'], 'Sunny')

    def test_guest_can_send_and_persist_a_message_without_a_nickname(self):
        async def send_guest_message():
            communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/')
            communicator.scope['session'] = {}
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()
            await communicator.send_json_to({'message': 'Hello as a guest'})
            response = await communicator.receive_json_from()
            await communicator.disconnect()
            return response

        response = async_to_sync(send_guest_message)()

        self.assertEqual(response['nickname'], 'Guest')
        self.assertIsNone(ChatMessage.objects.get().name)


class NicknameFlowTests(TransactionTestCase):
    def test_home_page_asks_for_an_optional_nickname(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Continue as a guest')
        self.assertContains(response, 'What should we call you?')

    def test_submitting_a_nickname_saves_it_in_session(self):
        response = self.client.post('/', {'nickname': '  Sunny  '})

        self.assertRedirects(response, '/chat/')
        nickname = Nickname.objects.get()
        self.assertEqual(nickname.nickname, 'Sunny')
        self.assertEqual(self.client.session['nickname_id'], nickname.pk)

    def test_guest_can_skip_nickname_and_chat(self):
        response = self.client.post('/', {'nickname': ''})

        self.assertRedirects(response, '/chat/')
        self.assertNotIn('nickname_id', self.client.session)
        self.assertEqual(self.client.get('/chat/').status_code, 200)

    def test_name_can_be_cleared_by_continuing_as_guest(self):
        nickname = Nickname.objects.create(nickname='Sunny')
        session = self.client.session
        session['nickname_id'] = nickname.pk
        session.save()

        response = self.client.post('/', {'nickname': ''})

        self.assertRedirects(response, '/chat/')
        self.assertNotIn('nickname_id', self.client.session)
