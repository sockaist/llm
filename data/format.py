import json
import os

"""
주어진 data 폴더 내의 모든 json 파일 형식에 "id"를 추가한다.
"id"는 파일명(정수형태)로 저장되므로, 파일명과 id를 동치로 생각해도 무방하다.

또한, "date"와 "start", "finish" 등 날짜가 포함된 필드의 형식을 하나로 맞춘다.
모든 형식은 QdrantDB에서 필터링하기 위해 ISO 8601 형식(YYYY-MM-DDT00:00:00Z)으로 통일한다.
(시간은 의미가 없으므로 모두 00:00:00Z로 설정)

date의 형식이 다음과 같은 형식이 아니라면 오류가 발생하며, 기존에 저장된 데이터를 삭제하므로 주의하자.
- 0000년 00월 00일
- 0000-00-00
- 0000.00.00

또한, qdrantdb의 효과적인 tokenize를 위해 json의 내용을 모두 담고 있는 content field를 추가한다.
이미 content field가 존재한다면(크롤링 단계에서 content를 생성하는 경우가 있다) 덮어쓰지 않는다.
"""


def time_formatter(str):
    try:
        if "." in str:
            return str.split(".")[0]+ "-" + str.split(".")[1] + "-" + str.split(".")[2] + "T00:00:00Z"
        elif "-" in str:
            return f"{int(str.split('-')[0]):04d}-{int(str.split('-')[1]):02d}-{int(str.split('T')[0].split('-')[2]):02d}T00:00:00Z"
        elif "일" in str:
            return str.split("년")[0] + "-" + str.split("년")[1].split("월")[0].strip() + "-" + str.split("월")[1].split("일")[0].strip() + "T00:00:00Z"
    except Exception as e:
        pass
folders = [f for f in os.listdir(".") if os.path.isdir(f)]

for folder in folders:
    details = [f for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]
    for detail in details:
        detail_path = os.path.join(folder, detail)
        json_files = [f for f in os.listdir(detail_path) if f.endswith(".json")]
        for filename in json_files:
            with open(os.path.join(detail_path, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                #ADD id field
                if "id" not in data:
                    if folder == "csweb":
                        data["id"] = int(filename.split(".")[0])
                    else:
                        data["id"] = int(filename.split("_")[1].split(".")[0])
                
                #Format date fields
                if folder == "notion":
                    if "finish" in data:
                        finish_str = data["finish"]
                        if(finish_str == None):
                            print(folder, filename)
                        data["finish"] = time_formatter(finish_str)
                        data["date"] = time_formatter(finish_str)
                else:
                    if "date" in data:
                        date_str = data["date"]
                        if(date_str == None):
                            print(folder, filename)
                        data["date"] = time_formatter(date_str)
                
                #Add content field
                if "content" not in data:
                    content = ""
                    for key, value in data.items():
                        if isinstance(value, str):
                            content += key+ ": " + value + " "
                        elif isinstance(value, list):
                            content += " ".join(value) + " "
                    data["content"] = content.strip()
                json.dump(data, open(os.path.join(detail_path, filename), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)