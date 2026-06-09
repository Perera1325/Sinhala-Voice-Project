import csv
import sys

sys.stdout.reconfigure(encoding='utf-8')

csv_path = r"C:\Users\Kasundi\Ofline Method\evaluation_results.csv"
try:
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        printed = 0
        for row in reader:
            if 'danna' in row.get('Expected_Cmd', '').lower():
                print(f"Expected: {row['Expected_Cmd']} | Vosk Transcribed: {row['Offline_ASR_Text']}")
                printed += 1
                if printed >= 20:
                    break
except Exception as e:
    print(f"Error reading CSV: {e}")
