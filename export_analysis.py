import sqlite3
import json
import numpy as np
from scipy.spatial.distance import cosine

DB_PATH = "voice_users.db"
EXPORT_PATH = "voice_dataset_export.json"

def analyze_and_export():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, embedding FROM users')
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    export_data = []
    
    for row in rows:
        uid, name, emb_json = row
        emb = json.loads(emb_json)
        users.append({"id": uid, "name": name, "embedding": np.array(emb)})
        export_data.append({"id": uid, "name": name, "features_mfcc": emb})
        
    # Export to JSON
    with open(EXPORT_PATH, "w") as f:
        json.dump(export_data, f, indent=4)
        
    print(f"SUCCESS: Exported {len(users)} voice profiles to {EXPORT_PATH}\n")
    print("="*50)
    print("VOICE BIOMETRIC ACCURACY ANALYSIS")
    print("="*50)
    print("Cross-referencing enrolled voices to determine distinctiveness (higher is better for different users):\n")
    
    for i in range(len(users)):
        for j in range(i + 1, len(users)):
            u1 = users[i]
            u2 = users[j]
            
            # Calculate Cosine Similarity
            # Note: We already normalized vectors in speaker_biometrics, but we do it again just to be safe
            norm1 = np.linalg.norm(u1["embedding"])
            norm2 = np.linalg.norm(u2["embedding"])
            
            if norm1 > 0 and norm2 > 0:
                similarity = 1 - cosine(u1["embedding"], u2["embedding"])
            else:
                similarity = 0
                
            match_percentage = similarity * 100
            
            # Analysis
            if u1["name"] == u2["name"]:
                print(f"SAME USER: {u1['name']} (ID {u1['id']}) vs {u2['name']} (ID {u2['id']}) -> {match_percentage:.1f}% Similarity (Expected > 80%)")
            else:
                if match_percentage > 60:
                    print(f"WARNING: {u1['name']} (ID {u1['id']}) vs {u2['name']} (ID {u2['id']}) -> {match_percentage:.1f}% Similarity (High risk of false match!)")
                else:
                    print(f"SECURE: {u1['name']} (ID {u1['id']}) vs {u2['name']} (ID {u2['id']}) -> {match_percentage:.1f}% Similarity (Safely distinct)")

if __name__ == "__main__":
    analyze_and_export()
