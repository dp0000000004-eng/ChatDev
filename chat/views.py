from django.shortcuts import redirect, render

from .forms import NicknameForm
from .models import ChatMessage, Nickname


def lobby(request):
    messages = list(
        ChatMessage.objects.select_related('name').order_by('-created_at', '-pk').values(
            'id', 'message', 'created_at', 'name__nickname'
        )[:100]
    )
    messages.reverse()
    for message in messages:
        message['nickname'] = message.pop('name__nickname') or 'Guest'

    return render(request, 'chat.html', {
        'chat_messages': messages,
    })


def get_name(request):
    if request.method == 'POST':
        form = NicknameForm(request.POST)
        if form.is_valid():
            nickname_text = form.cleaned_data['nickname']
            if nickname_text:
                nickname = Nickname.objects.create(nickname=nickname_text)
                request.session['nickname_id'] = nickname.pk
            else:
                request.session.pop('nickname_id', None)

            return redirect('lobby')
    else:
        nickname = Nickname.objects.filter(
            pk=request.session.get('nickname_id')
        ).first()
        form = NicknameForm(initial={
            'nickname': nickname.nickname if nickname else '',
        })

    return render(request, 'ask.html', {'form': form})