from django.shortcuts import render

from .models import ChatMessage


def lobby(request):
    messages = list(
        ChatMessage.objects.order_by('-created_at', '-pk').values(
            'id', 'message', 'created_at'
        )[:100]
    )
    messages.reverse()
    return render(request, 'chat.html', {'chat_messages': messages})
