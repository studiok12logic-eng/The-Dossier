from django import forms
from .models import Target, TargetGroup, CustomAnniversary
import datetime

# --- GLOBAL STYLES ---
# "BG 2 levels brighter" from bg-black/20 -> bg-white/5
# "Border 1 level brighter" from border-white/10 -> border-white/20
STYLE_INPUT = 'w-full bg-white/5 border border-white/20 rounded px-4 py-2 text-white focus:outline-none focus:border-primary'
STYLE_SELECT = 'w-full bg-white/5 border border-white/20 rounded px-4 py-2 text-white focus:outline-none focus:border-primary appearance-none cursor-pointer'
STYLE_CHECKBOX = 'rounded border-gray-600 text-primary bg-gray-900 w-4 h-4 mr-2'
STYLE_FILE = 'w-full bg-white/5 border border-white/20 rounded px-4 py-2 text-white focus:outline-none focus:border-primary file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-black hover:file:bg-primary/80'

class TargetForm(forms.ModelForm):
    # Split name fields
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': '姓'}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': '名'}))
    last_name_kana = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': 'せい'}))
    first_name_kana = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': 'めい'}))
    
    # Birthdate split fields
    birth_year = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': STYLE_INPUT, 'placeholder': '年'}))
    birth_month = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': STYLE_INPUT, 'placeholder': '月', 'min': 1, 'max': 12}))
    birth_day = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': STYLE_INPUT, 'placeholder': '日', 'min': 1, 'max': 31}))
    
    # Zodiac (Read-only or Hidden, calculated by JS)
    zodiac_sign = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': STYLE_INPUT, 'readonly': 'readonly'}))

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

        if self.instance and self.instance.pk:
            self.fields['birth_year'].initial = self.instance.birth_year
            self.fields['birth_month'].initial = self.instance.birth_month
            self.fields['birth_day'].initial = self.instance.birth_day

    class Meta:
        model = Target
        fields = ['nickname', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana', 
                  'birthplace', 'gender', 'blood_type', 'description', 'avatar', 'zodiac_sign', 'groups']
        widgets = {
            'nickname': forms.TextInput(attrs={'class': STYLE_INPUT, 'required': 'required'}),
            'birthplace': forms.TextInput(attrs={'class': STYLE_INPUT}),
            'gender': forms.Select(attrs={'class': STYLE_SELECT}),
            'blood_type': forms.Select(attrs={'class': STYLE_SELECT}),
            'description': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 4}),
            'avatar': forms.FileInput(attrs={'class': STYLE_FILE}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Combine birth fields
        instance.birth_year = self.cleaned_data.get('birth_year')
        instance.birth_month = self.cleaned_data.get('birth_month')
        instance.birth_day = self.cleaned_data.get('birth_day')
        
        if commit:
            instance.save()
            self.save_m2m() # Save groups
        return instance

class TargetGroupForm(forms.ModelForm):
    class Meta:
        model = TargetGroup
        fields = ['name', 'description', 
                  'is_mon', 'is_tue', 'is_wed', 'is_thu', 'is_fri', 'is_sat', 'is_sun']
        widgets = {
            'name': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': 'グループ名'}),
            'description': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 2, 'placeholder': '説明'}),
            'is_mon': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'is_tue': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'is_wed': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'is_thu': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'is_fri': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'is_sat': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
            'is_sun': forms.CheckboxInput(attrs={'class': STYLE_CHECKBOX}),
        }


class CustomAnniversaryForm(forms.ModelForm):
    class Meta:
        model = CustomAnniversary
        fields = ['label', 'date']
        widgets = {
            'label': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': '名称'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': STYLE_INPUT}),
        }

# --- QUESTION MANAGEMENT ---
from .models import Question, QuestionCategory, QuestionRank
from django.contrib.auth import get_user_model

class QuestionCategoryForm(forms.ModelForm):
    class Meta:
        model = QuestionCategory
        fields = ['name', 'order', 'is_shared']
        widgets = {
            'name': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': 'カテゴリー名'}),
            'order': forms.NumberInput(attrs={'class': 'w-32 bg-white/5 border border-white/20 rounded px-3 py-2 text-white'}), # Custom width for order
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Hide 'order' and 'is_shared' for non-MASTER, or just don't include them in fields if not MASTER?
        # Requirement: "MASTER以外は...表示順項目は非表示"
        if self.user and getattr(self.user, 'role', '') != 'MASTER':
             if 'order' in self.fields: del self.fields['order']
             if 'is_shared' in self.fields: del self.fields['is_shared']

    def clean_name(self):
        name = self.cleaned_data['name']
        from django.db.models import Q
        # Validation: No duplicate name in (User's own OR Shared)
        # Exclude self if editing
        qs = QuestionCategory.objects.filter(
            Q(user=self.user) | Q(is_shared=True),
            name=name
        )
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise forms.ValidationError(f"カテゴリー「{name}」は既に存在します。")
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and getattr(self.user, 'role', '') == 'MASTER':
            instance.is_shared = True
        if commit:
            instance.save()
        return instance

class QuestionRankForm(forms.ModelForm):
    class Meta:
        model = QuestionRank
        fields = ['name', 'points']
        widgets = {
            'name': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': 'ランク名'}),
            'points': forms.NumberInput(attrs={'class': STYLE_INPUT, 'placeholder': 'ポイント'}),
        }

class CategoryModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.description:
            return f"{obj.name} : {obj.description}"
        return obj.name

class QuestionForm(forms.ModelForm):
    # Custom field to display Description and make Required=True
    category = CategoryModelChoiceField(
        queryset=QuestionCategory.objects.none(),
        required=True, # Enforce selection
        widget=forms.Select(attrs={'class': STYLE_SELECT}),
        empty_label="カテゴリーを選択してください"
    )

    class Meta:
        model = Question
        fields = ['is_shared', 'category', 'rank', 'title', 'description', 'example', 'answer_type', 'choices', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': STYLE_INPUT}),
            'description': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 3}), # Adjusted rows
            'example': forms.Textarea(attrs={'class': STYLE_INPUT, 'rows': 2}),
            'choices': forms.TextInput(attrs={'class': STYLE_INPUT, 'placeholder': '例: はい, いいえ, 多分'}),
            'order': forms.NumberInput(attrs={'class': 'w-32 bg-white/5 border border-white/20 rounded px-3 py-2 text-white'}),
            # Explicitly define Selects with STYLE_SELECT 
            # category is handled by class field above
            'rank': forms.Select(attrs={'class': STYLE_SELECT}),
            'answer_type': forms.Select(attrs={'class': STYLE_SELECT}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) # Store user
        super().__init__(*args, **kwargs)
        
        is_master = False
        if self.user and hasattr(self.user, 'role') and self.user.role == 'MASTER':
            is_master = True

        if self.user:
            # Category QuerySet
            # User can pick from Shared Categories.
            # Master can pick from Own + Shared
            from django.db.models import Q
            if is_master:
                self.fields['category'].queryset = QuestionCategory.objects.filter(Q(user=self.user) | Q(is_shared=True))
                self.fields['rank'].queryset = QuestionRank.objects.filter(user=self.user)
            else:
                # Non-Master: Can only pick Shared Categories
                self.fields['category'].queryset = QuestionCategory.objects.filter(is_shared=True)
                
            if not is_master:
                # Remove protected fields
                cols_to_remove = ['is_shared', 'order', 'rank']
                for col in cols_to_remove:
                    if col in self.fields:
                        del self.fields[col]
        else:
             self.fields['category'].queryset = QuestionCategory.objects.none()
             self.fields['rank'].queryset = QuestionRank.objects.none()

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Enforce defaults for non-MASTER
        is_master = False
        if hasattr(self.user, 'role') and self.user.role == 'MASTER':
            is_master = True
            
        if not is_master and self.user:
            instance.is_shared = False
            instance.rank = None # No rank for non-master
        elif is_master:
            instance.is_shared = True
            
        if commit:
            instance.save()
        return instance

    def clean_title(self):
        title = self.cleaned_data['title']
        from django.db.models import Q
        # Validation: No duplicate title in (User's own OR Shared)
        qs = Question.objects.filter(
            Q(user=self.user) | Q(is_shared=True),
            title=title
        )
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError(f"質問「{title}」は既に存在します。")
        return title

class QuestionImportForm(forms.Form):
    file = forms.FileField(
        label='CSVファイル',
        widget=forms.FileInput(attrs={'class': STYLE_FILE, 'accept': '.csv'})
    )

