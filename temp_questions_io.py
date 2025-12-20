import csv
import io
import codecs
from django.db import transaction
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
from intelligence.models import Question, QuestionCategory, QuestionRank
from intelligence.forms import QuestionImportForm
import urllib.parse

class QuestionExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # 1. Fetch visible questions
        user = request.user
        questions = Question.objects.filter(
            Q(user=user) | Q(is_shared=True)
        ).select_related('category', 'rank').order_by('category__order', 'order')

        # 2. Prepare Response (Shift-JIS)
        filename = "questions_export.csv"
        quoted_filename = urllib.parse.quote(filename)
        
        response = HttpResponse(content_type='text/csv; charset=Shift-JIS')
        response['Content-Disposition'] = f'attachment; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}'
        
        # 3. CSV Writer
        # Helper to clean text for Shift-JIS
        def clean(text):
            if text is None: return ""
            text = str(text)
            return text.encode('cp932', 'replace').decode('cp932')
            
        writer = csv.writer(response)
        
        # Header
        # 入力列｜カテゴリー名｜共通質問｜表示順｜ランク｜質問名｜説明・意図｜質問例｜回答形式｜選択肢
        header = ['入力列', 'カテゴリー名', '共通質問', '表示順', 'ランク', '質問名', '説明・意図', '質問例', '回答形式', '選択肢']
        writer.writerow([clean(h) for h in header])
        
        for q in questions:
            row = [
                '', # Input column (Empty for export)
                q.category.name if q.category else '未分類',
                'TRUE' if q.is_shared else 'FALSE',
                q.order,
                q.rank.name if q.rank else '',
                q.title,
                q.description,
                q.example,
                q.get_answer_type_display(), # '選択式' or '自由記述'
                q.choices
            ]
            writer.writerow([clean(col) for col in row])
            
        return response

class QuestionImportView(LoginRequiredMixin, View):
    template_name = 'question_import.html'
    
    def get(self, request):
        form = QuestionImportForm()
        return render(request, self.template_name, {'form': form})
        
    def post(self, request):
        form = QuestionImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
            
        csv_file = request.FILES['file']
        
        # 1. Detect Encoding
        # Read a chunk to detect
        sample = csv_file.read(2048)
        csv_file.seek(0)
        encoding = 'utf-8'
        try:
            sample.decode('utf-8')
        except UnicodeDecodeError:
            encoding = 'cp932' # Shift-JIS fallback
            
        # 2. Read lines
        try:
            # Use TextIOWrapper
            io_text = io.TextIOWrapper(csv_file, encoding=encoding, newline='')
            reader = csv.reader(io_text)
            rows = list(reader)
        except Exception as e:
            return render(request, self.template_name, {'form': form, 'error_msg': f'ファイルの読み込みに失敗しました: {str(e)}'})

        if not rows:
             return render(request, self.template_name, {'form': form, 'error_msg': 'CSVファイルが空です。'})

        # Headers check (Skip row 0)
        # Expected index map
        # 0:Input, 1:Cat, 2:Shared, 3:Order, 4:Rank, 5:Title, 6:Desc, 7:Ex, 8:Type, 9:Choices
        
        # 3. Processing
        logs = []
        errors = []
        success_count = 0
        
        try:
            with transaction.atomic():
                for idx, row in enumerate(rows):
                    if idx == 0: continue # Skip header
                    if len(row) < 6: # At least up to Title
                         continue
                         
                    line_no = idx + 1
                    input_act = row[0].strip().lower()
                    cat_name = row[1].strip()
                    is_shared_str = row[2].strip().upper()
                    order_str = row[3].strip()
                    rank_name = row[4].strip()
                    title = row[5].strip()
                    desc = row[6].strip() if len(row) > 6 else ""
                    example = row[7].strip() if len(row) > 7 else ""
                    type_str = row[8].strip() if len(row) > 8 else "自由記述"
                    choices = row[9].strip() if len(row) > 9 else ""
                    
                    if not input_act:
                        logs.append(f"{line_no}行目: スキップ (入力列が空)")
                        continue
                    if input_act not in ['n', 'u', 'd']:
                        logs.append(f"{line_no}行目: スキップ (入力列 '{input_act}' は無効)")
                        continue
                        
                    if not title:
                         errors.append(f"{line_no}行目: 質問名が必須です。")
                         continue
                         
                    # -- Validation & Preparation --
                    
                    # Category
                    category = None
                    if not cat_name:
                         cat_name = 'Unclassified' # Default? or Error? Specs said default unclassified on empty
                         # Spec: "空欄時のデフォルト設定 カテゴリー名＝アンクラシファイド"
                         
                    # Find Category
                    # Search In: User's or Shared.
                    # Creating new category? Spec doesn't strictly say. 
                    # Spec: "カテゴリー名が違う場合＝エラー ｘ行目：入力したカテゴリー名が見つかりませんでした。"
                    # So strict search.
                    # BUT Spec also says "Default = Unclassified". So if empty, looking for Unclassified.
                    if not cat_name: cat_name = 'Unclassified'
                    
                    category = QuestionCategory.objects.filter(
                        Q(user=request.user) | Q(is_shared=True),
                        name=cat_name
                    ).first()
                    
                    if not category:
                         if cat_name == 'Unclassified':
                              # Allow auto-create for default? Or error?
                              # Let's error strictly as per spec "入力したカテゴリー名が見つかりませんでした"
                              errors.append(f"{line_no}行目: カテゴリー「{cat_name}」が見つかりませんでした。")
                              continue
                         else:
                              errors.append(f"{line_no}行目: カテゴリー「{cat_name}」が見つかりませんでした。")
                              continue

                    # Rank
                    rank = None
                    if rank_name and rank_name != 'Null':
                        rank = QuestionRank.objects.filter(user=request.user, name=rank_name).first()
                        if not rank:
                             # Try shared? Rank is user specific usually?
                             # Model: QuestionRank user=FK. Not shared.
                             # If MASTER, they have ranks. If AGENT, they have ranks.
                             # Maybe rank name mismatch.
                             errors.append(f"{line_no}行目: ランク「{rank_name}」が見つかりませんでした。")
                             continue
                    
                    # Type
                    # 自由記述 or 選択式
                    answer_type = 'TEXT'
                    if type_str == '選択式':
                        answer_type = 'SELECTION'
                        if not choices:
                             errors.append(f"{line_no}行目: 選択式を選んだ場合、選択肢は必須です。")
                             continue
                    elif type_str == '自由記述':
                        answer_type = 'TEXT'
                    else:
                         errors.append(f"{line_no}行目: 回答形式「{type_str}」が見つかりませんでした。")
                         continue
                         
                    # Is Shared
                    is_shared = False
                    if is_shared_str == 'TRUE': is_shared = True
                    
                    # Order
                    try:
                        order = int(order_str) if order_str else 0
                    except ValueError:
                        order = 0

                    # -- Execution --
                    
                    # Check duplication
                    # Search existing question by Title
                    existing_q = Question.objects.filter(
                        Q(user=request.user) | Q(is_shared=True),
                        title=title
                    ).first()
                    
                    if input_act == 'n': # New
                        if existing_q:
                            errors.append(f"{line_no}行目: 同じ質問名の質問が存在します。")
                            continue
                        
                        Question.objects.create(
                            user=request.user,
                            category=category,
                            rank=rank,
                            title=title,
                            description=desc,
                            example=example,
                            answer_type=answer_type,
                            choices=choices,
                            is_shared=is_shared,
                            order=order
                        )
                        success_count += 1
                        
                    elif input_act == 'u': # Update
                        if not existing_q:
                            errors.append(f"{line_no}行目: 更新対象の質問「{title}」が見つかりませんでした。")
                            continue
                        
                        # Update fields
                        existing_q.category = category
                        existing_q.rank = rank
                        existing_q.description = desc
                        existing_q.example = example
                        existing_q.answer_type = answer_type
                        existing_q.choices = choices
                        existing_q.is_shared = is_shared
                        existing_q.order = order
                        existing_q.save()
                        success_count += 1
                        
                    elif input_act == 'd': # Delete
                        if not existing_q:
                             logs.append(f"{line_no}行目: 削除対象の質問「{title}」が見つかりませんでした（スキップ）。")
                             continue
                        existing_q.delete()
                        success_count += 1

                if errors:
                    # If any error, RAISE exception to rollback
                    raise Exception("Validation Error")
                    
        except Exception as e:
            if str(e) == "Validation Error":
                pass # Handled by returning errors
            else:
                errors.append(f"システムエラー: {str(e)}")
        
        if errors:
            return render(request, self.template_name, {
                'form': form, 
                'error_list': errors,
                'logs': logs
            })
            
        return render(request, self.template_name, {
            'form': form,
            'success_msg': f'{success_count}件の処理が完了しました。',
            'logs': logs
        })
