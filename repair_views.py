import os

path = 'core/views.py'
temp_path = 'temp_target_export_view.py'

try:
    with open(path, 'rb') as f:
        content_bytes = f.read()
        # Decode ignoring errors to skip garbage
        content = content_bytes.decode('utf-8', 'ignore')

    lines = content.splitlines(keepends=True)

    idx = -1
    for i, line in enumerate(lines):
        if 'class HelpView' in line:
            idx = i

    if idx != -1:
        # HelpView typically:
        # 1. class HelpView(...)
        # 2.     template_name = ...
        # 3.     mobile_template_name = ...
        # 4. (EOF or newline)
        cutoff = idx + 3
        # Validate that lines around cutoff are what we expect, just in case
        print(f"HelpView found at {idx}. Keeping until {cutoff}.")
        
        cleaned_lines = lines[:cutoff]
        for l in cleaned_lines[-3:]:
            print(f"Keep: {l.strip()}")

        with open(temp_path, 'r', encoding='utf-8') as f:
            new_code = f.read()

        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
            f.write('\n\n')
            f.write(new_code)
        print("Success: views.py repaired and new code appended.")
    else:
        print("Error: HelpView not found.")
except Exception as e:
    print(f"Exception: {e}")
