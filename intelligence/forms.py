from django import forms
from .models import Question, QuestionCategory, QuestionRank

class QuestionCategoryForm(forms.ModelForm):
    class Meta:
        model = QuestionCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-surface border border-white/10 rounded px-3 py-2 text-white', 'placeholder': 'カテゴリー名'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-surface border border-white/10 rounded px-3 py-2 text-white h-20', 'placeholder': '説明'}),
        }

class QuestionRankForm(forms.ModelForm):
    class Meta:
        model = QuestionRank
        fields = ['name', 'points']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-surface border border-white/10 rounded px-3 py-2 text-white', 'placeholder': 'ランク名'}),
            'points': forms.NumberInput(attrs={'class': 'w-full bg-surface border border-white/10 rounded px-3 py-2 text-white', 'placeholder': 'ポイント'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['is_shared', 'category', 'rank', 'title', 'description', 'example', 'answer_type', 'choices', 'order']
        widgets = {
             # Styled in template or here? Let's add basic classes
            'title': forms.TextInput(attrs={'class': 'w-full bg-black/20 border border-white/10 rounded px-3 py-2 text-white'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-black/20 border border-white/10 rounded px-3 py-2 text-white h-24'}),
            'example': forms.Textarea(attrs={'class': 'w-full bg-black/20 border border-white/10 rounded px-3 py-2 text-white h-20'}),
            'choices': forms.TextInput(attrs={'class': 'w-full bg-black/20 border border-white/10 rounded px-3 py-2 text-white', 'placeholder': '例: はい, いいえ, 多分'}),
            'order': forms.NumberInput(attrs={'class': 'w-32 bg-black/20 border border-white/10 rounded px-3 py-2 text-white'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = QuestionCategory.objects.filter(user=user)
            self.fields['rank'].queryset = QuestionRank.objects.filter(user=user)
