import os
import json
import glob
import time
import asyncio
from typing import Dict

import openai
from dotenv import load_dotenv

# Ensure src is in path
import sys
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

# Load env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in environment.")
    sys.exit(1)

client = openai.OpenAI(api_key=OPENAI_API_KEY)

TARGET_DIR = "data/csweb/research"

def generate_biography(profile: Dict) -> str:
    """Generate a rich academic biography from structured profile data."""
    
    # Construct a prompt based on available fields
    name = profile.get("name", "Unknown")
    lab = profile.get("lab", "") or profile.get("intro", "")
    field = profile.get("field", "")
    homepage = profile.get("web", "")
    
    prompt = f"""
    You are an academic writer. Write a detailed, professional 1-paragraph biography (approx 200 words) for a Computer Science professor/researcher based on this metadata:
    
    Name: {name}
    Research Area: {field}
    Lab/Intro: {lab}
    Website: {homepage}
    
    Format:
    - Start with "{name} is a..."
    - Elaborate on their likely research topics based on the 'Research Area'. EXPAND on the keywords to include related technical terms (e.g., if 'AI', mention 'Deep Learning', 'Neural Networks').
    - Mention their lab context if available.
    - Keep it factual but descriptive (Dense Retrieval friendly).
    - Language: Korean (but include English technical terms in brackets).
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for expanding academic profiles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   ⚠️ Error generating bio for {name}: {e}")
        return ""

async def main():
    print(f"🚀 Starting Document Expansion for {TARGET_DIR}...")
    
    files = glob.glob(os.path.join(TARGET_DIR, "*.json"))
    print(f"📂 Found {len(files)} profiles.")
    
    updated_count = 0
    skipped_count = 0
    
    for fpath in files:
        changed = False
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Check if already expanded
        if "biography" in data and len(data["biography"]) > 50:
            print(f"⏩ Skipping {data.get('name')} (Already expanded)")
            skipped_count += 1
            continue
            
        print(f"✨ Generating bio for: {data.get('name')}")
        bio = generate_biography(data)
        
        if bio:
            data["biography"] = bio
            
            # Prepend to content for indexing
            original_content = data.get("content", "")
            # Avoid double prepend
            if bio not in original_content:
                data["content"] = f"{bio}\n\n{original_content}"
                
            changed = True
            
        if changed:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            updated_count += 1
            time.sleep(0.5) # Rate limit politeness
            
    print("\n✅ Finished Expansion.")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")

if __name__ == "__main__":
    asyncio.run(main())
