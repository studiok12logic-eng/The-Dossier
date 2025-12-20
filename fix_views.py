
import os

file_path = 'core/views.py'

try:
    with open(file_path, 'rb') as f:
        content = f.read()

    # Strip null bytes
    clean_content = content.replace(b'\x00', b'')
    
    # Attempt to decode
    try:
        text = clean_content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = clean_content.decode('shift_jis')
        except UnicodeDecodeError:
            # Fallback: decode with errors ignore
            text = clean_content.decode('utf-8', errors='ignore')
            print("Warning: Decoded with errors.")

    # Write back as clean UTF-8
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    print(f"Successfully repaired {file_path}")

except Exception as e:
    print(f"Error: {e}")
