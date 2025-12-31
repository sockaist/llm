import glob
import json
import os

DATA_DIR = "data/csweb/research"

def analyze_research_data():
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    total = len(files)
    
    empty_etc = 0
    short_content = 0 # < 100 chars
    rich_content = 0
    
    lengths = []
    
    print(f"📊 Analyzing {total} documents in {DATA_DIR}...")
    
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            etc = data.get("etc", "").strip()
            content = data.get("content", "").strip()
            
            lengths.append(len(content))
            
            if not etc or len(etc) < 10:
                empty_etc += 1
            
            if len(content) < 100:
                short_content += 1
            else:
                rich_content += 1
                
    print(f"   - Total: {total}")
    print(f"   - Empty/Short 'etc' (<10 chars): {empty_etc} ({empty_etc/total*100:.1f}%)")
    print(f"   - Short 'content' (<100 chars): {short_content} ({short_content/total*100:.1f}%)")
    print(f"   - Rich 'content' (>=100 chars): {rich_content} ({rich_content/total*100:.1f}%)")
    
    avg_len = sum(lengths) / total if total else 0
    print(f"   - Average Content Length: {avg_len:.0f} chars")

if __name__ == "__main__":
    analyze_research_data()
