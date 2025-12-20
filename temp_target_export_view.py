import csv
import urllib.parse
from django.http import HttpResponse

class TargetExportView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        # 1. Check Permissions (MASTER or ELITE_AGENT only)
        if request.user.role not in [CustomUser.MASTER, CustomUser.ELITE_AGENT]:
             return render(request, '403.html', status=403) # Or simple HttpResponseForbidden

        target = get_object_or_404(Target, pk=pk, user=request.user)
        
        # 2. Prepare Response (Shift-JIS)
        # Handle filename encoding for various browsers (URL encode usually safe)
        filename = f"{target.nickname}_dossier_export.csv"
        quoted_filename = urllib.parse.quote(filename)
        
        response = HttpResponse(content_type='text/csv; charset=Shift-JIS')
        response['Content-Disposition'] = f'attachment; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}'
        
        # Wrapper to handle encoding errors (replace chars not in Shift-JIS)
        # Since csv.writer writes strings and HttpResponse encodes them, we need to ensure
        # the strings we pass contain only characters representable in Shift-JIS
        # OR we rely on Python's error handling. 
        # But HttpResponse using charset='Shift-JIS' might raise UnicodeEncodeError if content has unmappable chars.
        # Strategy: Clean data before passing to writer.
        
        def clean(text):
            if text is None: return ""
            text = str(text)
            # Replace unmappable characters with '?'
            return text.encode('cp932', 'replace').decode('cp932')

        writer = csv.writer(response)

        # 3. Row 1: Profile Headers
        header_row1 = [
            'ニックネーム', '姓名', 'せいめい', '生年月日', '年齢', '干支', 
            '星座', '性別', '血液型', '出身地', '所属グループ', '記念日'
        ]
        writer.writerow([clean(h) for h in header_row1])

        # 4. Row 2: Profile Data
        # Groups
        groups_str = " ".join([g.name for g in target.groups.all()])
        
        # Anniversaries
        annivs = []
        if target.birth_month and target.birth_day:
             annivs.append(f"誕生日({target.birth_month}/{target.birth_day})")
        for ca in target.customanniversary_set.all():
             annivs.append(f"{ca.label}({ca.date.month}/{ca.date.day})")
        annivs_str = " ".join(annivs)
        
        # Full Name & Kana
        full_name = f"{target.last_name} {target.first_name}".strip()
        full_name_kana = f"{target.last_name_kana} {target.first_name_kana}".strip()
        
        # Birthdate
        birth_date = ""
        if target.birth_year and target.birth_month and target.birth_day:
            birth_date = f"{target.birth_year}/{target.birth_month}/{target.birth_day}"
        elif target.birth_month and target.birth_day:
             birth_date = f"--/{target.birth_month}/{target.birth_day}"

        data_row1 = [
            target.nickname,
            full_name,
            full_name_kana,
            birth_date,
            target.age if target.age else "",
            target.eto if target.eto else "",
            target.zodiac_hiragana, # Use property
            target.get_gender_display(),
            target.get_blood_type_display(),
            target.birthplace,
            groups_str,
            annivs_str
        ]
        writer.writerow([clean(d) for d in data_row1])
        
        # 5. Row 3: Log Headers
        header_row2 = [
            '発生日', 'ニックネーム', '接触有無', 'イベント・質問', '内容', 
            'タグ', '質問名', '回答', '入力日', '更新日'
        ]
        writer.writerow([clean(h) for h in header_row2])
        
        # 6. Row 4+: Log Data
        # Fetch generic timeline items (Logs) AND Question answers.
        # Requirement: "インテリジェンス・ログ" which usually means TimelineItems.
        # Sorted by date desc
        
        items = TimelineItem.objects.filter(target=target).prefetch_related('tags', 'question').order_by('-date', '-created_at')
        
        for item in items:
            # Type mapping
            # USER REQUEST: "イベント・質問"
            # TYPE_CHOICES: Contact, Note, Event, Question
            item_type = item.type
            if item.type == 'Question':
                item_type = '質問'
            elif item.type == 'Contact':
                item_type = '接触'
            elif item.type == 'Event':
                 item_type = 'イベント'
            elif item.type == 'Note':
                 item_type = 'メモ'
            
            # Tags
            tags_str = " ".join([t.name for t in item.tags.all()])
            
            # Contact Made
            contact_str = "有" if item.contact_made else "無"
            
            # Question specific
            q_title = ""
            q_answer = ""
            content = item.content
            
            if item.type == 'Question':
                if item.question:
                    q_title = item.question.title
                # For questions, 'content' stores the answer usually?
                # Check model: question_answer field exists but content is also used?
                # Views.py logic uses `item.content` for answer.
                q_answer = item.content
                content = "" # "内容" requested separate from "回答"? 
                # Request says: 質問名｜回答. "内容" is col 5. "回答" is col 8.
                # If it's a question, maybe "内容" is empty and "回答" has the answer?
                # Or "内容" has the full text?
                # Let's put answer in "回答" and keep "内容" as is (which is answer in current DB design basically).
                # Actually, let's duplicate or leave content empty if it's purely Q&A.
                # User req: "内容" ... "回答".
                # I will put item.content into "回答" for Questions, and item.content into "内容" for others.
                if item.type == 'Question':
                     content = "" 
                
            else:
                # Normal log
                content = item.content
            
            # Dates
            date_str = item.date.strftime('%Y/%m/%d')
            created_str = item.created_at.astimezone().strftime('%Y/%m/%d %H:%M')
            # Update date fallback
            updated_str = created_str # TimelineItem has no updated_at
            
            row = [
                date_str,
                target.nickname,
                contact_str,
                item_type,
                content,
                tags_str,
                q_title,
                q_answer,
                created_str,
                updated_str
            ]
            writer.writerow([clean(col) for col in row])

        return response
