from django.db import models


class ChatMessage(models.Model):
    message = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('created_at', 'pk')

    def __str__(self):
        return self.message[:80]
