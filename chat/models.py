from django.db import models




class Nickname(models.Model):
    nickname = models.CharField(max_length=24, blank=True, null=True)

    def __str__(self):
        return self.nickname or 'Guest'



class ChatMessage(models.Model):
    name = models.ForeignKey(Nickname, on_delete=models.CASCADE, related_name="nick_name", blank=True, null=True)
    message = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('created_at', 'pk')

    def __str__(self):
        return self.message[:80]
