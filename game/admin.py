from django.contrib import admin
from .models import Profile, GameRecord, WordProblem

admin.site.register(Profile)
admin.site.register(GameRecord)

@admin.register(WordProblem)
class WordProblemAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'answer', 'topic', 'difficulty')
    list_filter = ('topic', 'difficulty')
    search_fields = ('question_text',)