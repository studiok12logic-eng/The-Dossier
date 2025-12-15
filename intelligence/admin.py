from django.contrib import admin
from .models import Question, Target, TargetGroup, Quest, Tag, DailyTargetState, CustomAnniversary, TimelineItem

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'rank', 'is_shared', 'user', 'order')
    list_filter = ('is_shared', 'user', 'category', 'rank')
    search_fields = ('title', 'description')
    ordering = ('order',)

admin.site.register(Question, QuestionAdmin)
admin.site.register(Target)
admin.site.register(TargetGroup)
admin.site.register(Quest)
admin.site.register(Tag)
admin.site.register(DailyTargetState)
admin.site.register(CustomAnniversary)
admin.site.register(TimelineItem)
