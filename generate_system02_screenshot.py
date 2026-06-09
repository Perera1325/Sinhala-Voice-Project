import os
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import ImageFormatter

out_dir = "Thesis_Code_Screenshots"
os.makedirs(out_dir, exist_ok=True)

# Capturing lines 28 to 44 of speaker_biometrics.py which shows the core MFCC extraction
# and the critical logic of dropping the 0th coefficient to guarantee zero-shot accuracy.
file_info = {"path": "src/speaker_biometrics.py", "name": "6_System_02_Hybrid_Biometrics.png", "lexer": "python", "lines": (28, 44)}

try:
    with open(file_info["path"], "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    start, end = file_info["lines"]
    code_snippet = "".join(lines[start:end])
    
    lexer = get_lexer_by_name(file_info["lexer"])
    formatter = ImageFormatter(font_size=18, style="monokai", line_numbers=True)
    
    out_path = os.path.join(out_dir, file_info["name"])
    with open(out_path, "wb") as out_f:
        out_f.write(highlight(code_snippet, lexer, formatter))
        
    print(f"Generated screenshot: {out_path}")
except Exception as e:
    print(f"Failed to generate {file_info['name']}: {e}")
