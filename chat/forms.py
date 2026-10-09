from django import forms


class NicknameForm(forms.Form):
    nickname = forms.CharField(
        max_length=24,
        required=False,
        strip=True,
        widget=forms.TextInput(attrs={
            'class': 'name-input',
            'autocomplete': 'nickname',
            'maxlength': 24,
            'placeholder': 'What should we call you?',
        }),
    )
