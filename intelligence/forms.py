from django import forms
from .models import Target, TargetGroup, CustomAnniversary
import datetime

class TargetForm(forms.ModelForm):
    # Split name fields
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'placeholder': '姓'}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'placeholder': '名'}))
    last_name_kana = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'placeholder': 'せい'}))
    first_name_kana = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'placeholder': 'めい'}))
    
    # Birthdate split fields
    birth_year = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'placeholder': '年'}))
    birth_month = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'placeholder': '月', 'min': 1, 'max': 12}))
    birth_day = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'placeholder': '日', 'min': 1, 'max': 31}))
    
    # Zodiac (Read-only or Hidden, calculated by JS)
    zodiac_sign = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'readonly': 'readonly'}))

    # Groups (M2M) - Rendered as checkbox or multi-select. Using SelectMultiple for now with custom styling class.
    # Groups (M2M) - Rendered as checkbox or multi-select. Using SelectMultiple for now with custom styling class.
    groups = forms.ModelMultipleChoiceField(
        queryset=TargetGroup.objects.none(), # Populated in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['groups'].queryset = TargetGroup.objects.filter(user=user)
        else:
             self.fields['groups'].queryset = TargetGroup.objects.none()

    class Meta:
        model = Target
        fields = ['nickname', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana', 
                  'birthplace', 'gender', 'blood_type', 'description', 'avatar', 'zodiac_sign', 'groups']
        widgets = {
            'nickname': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'required': 'required'}),
            'birthplace': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'gender': forms.Select(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'blood_type': forms.Select(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary', 'rows': 4}),
            'avatar': forms.FileInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:outline-none focus:border-primary file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-black hover:file:bg-primary/80'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Combine birth fields
        year = self.cleaned_data.get('birth_year')
        month = self.cleaned_data.get('birth_month')
        day = self.cleaned_data.get('birth_day')
        
        if year and month and day:
            try:
                instance.birthdate = datetime.date(year, month, day)
            except ValueError:
                pass # Invalid date
        
        if commit:
            instance.save()
            self.save_m2m() # Save groups
        return instance

class TargetGroupForm(forms.ModelForm):
    class Meta:
        model = TargetGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-surface border border-white/10 rounded px-4 py-2 text-white focus:border-primary', 'placeholder': 'グループ名'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-surface border border-white/10 rounded px-4 py-2 text-white focus:border-primary', 'rows': 2, 'placeholder': '説明'}),
        }

class CustomAnniversaryForm(forms.ModelForm):
    class Meta:
        model = CustomAnniversary
        fields = ['label', 'date']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:border-primary', 'placeholder': '記念日名称'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-surface/50 border border-white/10 rounded px-4 py-2 text-white focus:border-primary'}),
        }
