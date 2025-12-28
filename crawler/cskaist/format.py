import json
import os,sys

folder_path = "/Users/youngseocho/Desktop/socChatbot/crawler_cskaist/res"
json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]

for filename in json_files:
    words = filename.split(".")
    if words[0] != "csweb":
        print("incorrect format")
        break
    with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
        data = json.load(f)
        folder = words[1].split("_")[0]
        name = words[1].split("_")[1]
        json.dump(data, open(os.path.join(folder_path+"/csweb/"+folder, f"{name}.json"), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)