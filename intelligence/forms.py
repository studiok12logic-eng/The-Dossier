from django import forms
from .models import Target

class TargetForm(forms.ModelForm):
    class Meta:
        model = Target
        fields = ['name', 'nickname', 'rank', 'aliases', 'origin', 'gender', 'blood_type', 'birthdate', 'height', 'weight', 'description', 'avatar']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'nickname': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'rank': forms.Select(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'aliases': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'origin': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'gender': forms.Select(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'blood_type': forms.Select(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'birthdate': forms.DateInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'type': 'date'}),
            'height': forms.NumberInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'weight': forms.NumberInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'rows': 4}),
            'avatar': forms.FileInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-black hover:file:bg-primary/80'}),
        }
