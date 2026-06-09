import os
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import ImageFormatter

out_dir = "Thesis_Code_Screenshots"
os.makedirs(out_dir, exist_ok=True)

# Capturing the NLP Intent Classifier logic, specifically showing Sinhala keywords
# and handling the 'sam' edge case, which is perfect for System 03 documentation.
file_info = {"path": "src/nlp_classifier.py", "name": "7_System_03_NLP_Classifier.png", "lexer": "python", "lines": (14, 30)}

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
