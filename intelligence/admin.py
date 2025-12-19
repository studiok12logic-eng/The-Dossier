from django.contrib import admin
from .models import Question, Target, TargetGroup, Tag, DailyTargetState, CustomAnniversary, TimelineItem, QuestionCategory, QuestionRank

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'rank', 'is_shared', 'user', 'order')
    list_filter = ('is_shared', 'user', 'category', 'rank')
    search_fields = ('title', 'description')
    ordering = ('order',)

class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_shared', 'order', 'created_at')
    list_filter = ('is_shared', 'user')
    search_fields = ('name',)
    ordering = ('order', 'name')

class QuestionRankAdmin(admin.ModelAdmin):
    list_display = ('name', 'points', 'user', 'created_at')
    list_filter = ('user',)
    ordering = ('points',)

admin.site.register(Question, QuestionAdmin)
admin.site.register(Target)
admin.site.register(TargetGroup)
admin.site.register(QuestionCategory, QuestionCategoryAdmin)
admin.site.register(QuestionRank, QuestionRankAdmin)
admin.site.register(Tag)
admin.site.register(DailyTargetState)
admin.site.register(CustomAnniversary)
admin.site.register(TimelineItem)
