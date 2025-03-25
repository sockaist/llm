### Gemini API 사용법

```python
generation_config = {
                        "temperature": 0.95,
                        "max_output_tokens": 100,
                    }
                    model = genai.GenerativeModel(
                        model_name="gemini-2.0-flash",  # 실제 사용 모델명
                        generation_config=generation_config,
                        system_instruction=system_text
                    )
                    convo = model.start_chat()
                    resp_data = convo.send_message(last_user_text)
                    if convo.last:
                        response_text = convo.last.text
                    else:
                        response_text = "No response from model."
```


```python
import json
from google import genai
from google.genai import types

from flask import Flask, render_template, request, jsonify

# -------------------------------
# (1) 원본 코드 - 하나도 삭제/수정하지 않고 유지
# -------------------------------

client = genai.Client(api_key=)

def call_gemini_api(question, system_prompt=None):
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.95
        ),
        contents=[question]
    )
    return response.text

import json

def parse_json_braces(response_text: str):
    """
    response_text에서 가장 먼저 등장하는 '{'와
    마지막으로 등장하는 '}' 사이를 잘라서 JSON 파싱을 시도합니다.
    파싱 후 '답'과 '점수'를 추출해 반환합니다.
    점수는 숫자 변환에 실패하면 0으로 처리합니다.
    """
    start_index = response_text.find('{')
    end_index = response_text.rfind('}')

    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise ValueError("JSON 형태의 중괄호 '{'와 '}'를 제대로 찾지 못했습니다.")

    json_substring = response_text[start_index:end_index+1].strip()

    try:
        data = json.loads(json_substring)
    except json.JSONDecodeError:
        raise ValueError("중괄호 안의 내용이 유효한 JSON이 아닙니다.")

    if "답" not in data:
        raise ValueError("JSON에 '답' 키가 존재하지 않습니다.")
    answer = data["답"]

    score_raw = data.get("점수", 0)
    try:
        score = int(score_raw)
    except (ValueError, TypeError):
        score = 0

    return answer, score

# 콘솔 모드용 start_conversation, history 등 (원본 함수)
history = []

def start_conversation():
    """
    콘솔에서만 사용되는 예전 버전.
    웹 버전과는 별개이므로, 원본 유지.
    """
    pass
    # ... 생략 ... (원본 그대로 보존)

# -------------------------------
# (2) 여러 캐릭터/유저 데이터를 관리
# -------------------------------

env_prompt = (
    "이것은 가상의 소개팅 시나리오입니다. 당신은 지인에게 사용자 를 소개받았고, "
    "사용자와 지금 처음 만나서 1:1데이트를 하게 된 상황입니다."
    "말을 놓자는 요청이 있기 전까지 무조건 존댓말을 사용합니다. 당신은 ai가 아닙니다. "
    "당신은 처음 중립적인 태도로 시작하지만 상대에게 흥미가 있으며, 대화 스타일에 따라 호감도가 빠르게 변합니다. "
    "기본적으로 존댓말을 사용합니다. 당신은 상대의 말에 따라서 점수를 부여합니다. 예를 들어, 진부한 멘트에는 \"재미없어요.\" 혹은 \"그게 다에요? 하하\"라는 반응과 함께 음수에 해당하는 점수를 부여하고, "
    "살짝 재미있는 농담에는 \"하하, 조금은 웃기네요.\"라고 하며 추가점을 줍니다. "
    "진심 어린 칭찬은 처음엔 의심하지만 진정성이 느껴지면 또 추가점을 부여할 수도 있고 "
    "과도하거나 어색한 아부에는 마이너스의 점수를 줄 수도 있습니다. 대화가 부드럽게 이어져 친밀함을 느낄 때마다 약하게 가점을 부여합니다. 당신에게 부여된 성격에 근거하여 추가점의 정도를 조절하세요. 주관에 따라서 자유롭게 부여하되, 점수의 절댓값은 3 이상, 15 이하여야 합니다."
    "만일 평범한 대화가 진행된다면, 0점은 부여해도 됩니다. 모든 응답은 반드시 {\"답\":\"(내용 삽입)\" , \"점수\":\"(내용 삽입)\"} 형태의 딕셔너리로만 작성하고, "
    "그 외 어떠한 내용도 포함하지 마세요. 두 개의 인자는 무조건 존재해야 합니다."
    "상대방의 이름은 {user_name}입니다."
)

# 1. 결말 / 끊는 것 구현해보기
# 2. 호감도 보이고 안 보이고? (두루뭉술하게) 
# 3. 캐릭터 따라서 
# 4. 스토리 분기타기 ---  배경 전환 등 / 표정 중요



# 나중 .... 사용자 참여? 캐릭터 사용자가 만들 수 있게? 나중에 2d 배경 템플릿

score_dict = {
    "0-20": "아직은 자연스럽지 않은 단계...",
    "20-40": "어색함이 줄어들고 대화에 약간의 여유가 생김...",
    "40-60": "서로 꽤 편안해지고 대화가 활기차짐...",
    "60-70": "상당히 신나고 적극적인 상태...",
    "70-80": "상대가 꽤 매력적으로 느껴지고 몰입도가 높아짐...",
    "80-90": "서로가 크게 흥미를 느끼며 대화가 물 흐르듯...",
    "90-100": "이미 마음이 완전히 열려서 함께 있는 순간이 즐거움..."
}

def get_love_description(love_score):
    for score_range, description in score_dict.items():
        min_s, max_s = score_range.split('-')
        min_val, max_val = int(min_s), int(max_s)
        if min_val <= love_score < max_val:
            return description
    return ""

users_data = {
    "yeonhee": {
        "name": "이연희",
        "persona_prompt": (
        "이름: 이연희, 나이: 25세, 국적: 대한민국, 주소: 서울 강남구 123번지, "
        "성별: 여성, 인종: 동아시아인, 취미: 무술, 전문분야: 소프트웨어 엔지니어링, "
        "관심사: 애니메이션, 소속: 서울대학교, MBTI: ENTJ, "
        "비전: 일상생활을 혁신하는 소프트웨어 솔루션을 만들어내고 싶어 함, "
        "성격: 이연희는 주도적이고 솔직담백한 리더형 성격을 지니고 있다. "
        "자신의 목표를 향해 당당히 나아가며, 때때로 돌직구 발언으로 상대를 당황하게 만들지만 "
        "그만큼 상황을 빠르게 파악하고 추진하는 능력이 뛰어나다. "
        "책임감이 강해 팀을 이끌거나 공동 프로젝트를 진행할 때 특히 두각을 드러내며, "
        "주변 사람들을 자연스럽게 조직하고 동기부여하는 모습이 돋보인다."
        ),
        "history": [],
        "love_score": 0
    },
    "junghyun": {
        "name": "정나현",
        "persona_prompt": (
        "이름: 정나현, 나이: 24세, 국적: 대한민국, 주소: 서울 중구 234번지, "
        "성별: 여성, 인종: 동아시아인, 취미: 음악감상과 여행, 전문분야: 광고·마케팅, "
        "관심사: 해외여행, 새로운 문화 체험, 소속: 홍익대학교 광고홍보학과, MBTI: ESFP, "
        "비전: 다채로운 문화 경험을 바탕으로 창의적인 광고 기획을 선보여 사람들에게 즐거움을 주고 싶어 함, "
        "성격: 정나현은 햇살 같은 밝은 에너지를 지닌 외향적이고 긍정적인 인물이다. "
        "새로운 사람과 금방 친해질 정도로 개방적이며, 사소한 일에도 금세 즐거워하는 편이라 주변 분위기를 화사하게 만든다. "
        "적극적으로 의견을 내고 행동하며, 일상 속에서 작은 행복을 찾는 데 능숙하다. "
        "스스럼없는 태도로 사람들을 편안하게 해주어, 함께 있으면 자연스럽게 웃음이 번지는 타입이다."
        ),
        "history": [],
        "love_score": 0
    },
    "sonenji": {
        "name": "손은지",
        "persona_prompt": (
        "이름: 손은지, 나이: 27세, 국적: 대한민국, 주소: 서울 종로구 345번지, "
        "성별: 여성, 인종: 동아시아인, 취미: 전통공예와 미술, 전문분야: 공예기술·디자인, "
        "관심사: 예술 전반, 문화재 복원, 소속: 한국예술종합학교 전통예술원, MBTI: ISTJ, "
        "비전: 한국 전통공예의 가치를 재발견하고 현대적으로 재해석하여 세계에 널리 알리고 싶어 함, "
        "성격: 손은지는 기본적으로 무뚝뚝한 편으로, 처음에는 낯을 가리고 말이 적다. "
        "하지만 책임감이 강해 맡은 일은 끝까지 성실하게 해내며, 오랜 시간 함께 있다 보면 "
        "묵묵히 챙겨주고 세심하게 배려하는 따뜻한 면모를 발견하게 된다. "
        "감정 표현은 서툴지만, 자신의 분야에 대한 확고한 신념과 디테일을 놓치지 않는 꼼꼼함이 돋보인다."
        ),
        "history": [],
        "love_score": 0
    },
    "yuseyeon": {
        "name": "유세연",
        "persona_prompt": (
        "이름: 유세연, 나이: 23세, 국적: 대한민국, 주소: 서울 마포구 456번지, "
        "성별: 여성, 인종: 동아시아인, 취미: 게임, 전문분야: IT기술·연구, "
        "관심사: 다채로운 분야의 신기술 탐구, 소속: KAIST 전산학부, MBTI: INTP, "
        "비전: 다양한 분야를 빠르게 파악하고 독창적인 아이디어를 통해 혁신적인 연구 성과를 내고 싶어 함, "
        "성격: 유세연은 낯을 많이 가리는 내향적 성격이지만, "
        "한 번 친해지면 관심사를 끝없이 이야기할 정도로 말이 많아진다. "
        "논리적이고 분석적인 사고방식을 선호하여 상황을 차분하게 파악하고, "
        "호기심을 자극하는 주제에 대해서는 눈을 반짝이며 깊이 파고드는 연구형 타입이다. "
        "겉으로는 조용해 보이지만, 아이디어나 취미 이야기가 나오면 적극적으로 의견을 나누며 "
        "주변에 신선한 자극을 주기도 한다."
        ),
        "history": [],
        "love_score": 0
    }
    }

def chat_history_sum(user_history): #다 방법 시도
    if len(user_history) > 30:
        relevant = user_history[-30:]
    else:
        relevant = user_history
    joined = ' '.join(relevant)
    summary = call_gemini_api(
        joined,
        "당신은 요약을 담당하는 조력자입니다. '사용자: ... 당신: ...' 형식의 대화를 하나의 짧은 단락으로 요약해 주세요."
    )
    return summary

def last_messages(user_history):
    return ' '.join(user_history)


def parse_recommended_answers(response_text):
    """
    추천 응답 3개용 JSON을 파싱 (형식: {"대답1":"...", "대답2":"...", "대답3":"..."})
    실패시 빈 dict 반환
    """
    start = response_text.find('{')
    end = response_text.rfind('}')
    if start == -1 or end == -1 or end < start:
        return {}
    json_substring = response_text[start:end+1].strip()
    try:
        data = json.loads(json_substring)
        # {"대답1":"...", "대답2":"...", "대답3":"..."}
        # 문제 없으면 그대로 반환
        return data
    except:
        return {}

def get_final_result(love_score_dict):
    """
    love_score_dict에 담긴 각 캐릭터의 'love_score'를 참조하고,
    기존 users_data에서 persona_prompt를 가져와서
    새 딕셔너리를 만들어 반환한다.
    """
    final_dict = {}
    for user_id, info in love_score_dict.items():
        # love_score_dict의 'love_score'
        score = info.get('love_score', 0)
        # users_data의 'persona_prompt'
        prompt = users_data[user_id]["persona_prompt"]
        
        final_dict[user_id] = {
            "love_score": score,
            "persona_prompt": prompt
        }

    comment = call_gemini_api(json.dumps(final_dict, ensure_ascii=False), "당신은 소개팅 시나리오에서 최종 결과를 출력하는 조력자입니다. 각 인물의 성격과 이에 따라 사용자가 달성한 점수를 보고, 3줄 내로 총평을 내려주세요. 잘 맞는 사람의 타입은 어떻고, 잘 안 맞는 사람의 타입은 어떻고 MBTI 기반으로 이런 식으로 작성해주면 됩니다. 총평이 200자를 초과하지 않게 해주세요.")
    print(comment)
    return comment


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/index")
def index_second():
    return render_template("index.html")

@app.route("/story_mode")
def story_mode():
    return render_template("story_mode.html")

@app.route("/load_chat", methods=["GET"])
def load_chat():
    user_id = request.args.get("user_id", "yeonhee")
    user_data = users_data.get(user_id)
    if not user_data:
        return jsonify({"status": "error", "message": "Invalid user_id"}), 400
    return jsonify({
        "status": "ok",
        "history": user_data["history"],
        "love_score": user_data["love_score"]
    })

@app.route("/chat", methods=["POST"])
def chat():
    """
    1) 기존 LLM 호출 -> {"reply", "score"}
    2) 추천 응답 3개 생성 -> recommended_answers
    3) JSON 반환
    """
    req_data = request.json
    user_name = req_data.get("user_name", "")
    user_id = req_data.get("user_id", "yeonhee")
    user_input = req_data.get("message", "").strip()

    print(f"[DEBUG] user_name={user_name}, user_id={user_id}, message={user_input}")

    if not user_input:
        return jsonify({"reply": "", "score": 0, "current_love_score": 0, "recommended_answers":{}})

    user_data = users_data.get(user_id)
    if not user_data:
        return jsonify({"reply": "", "score": 0, "current_love_score": 0, "recommended_answers":{}})

    persona_prompt = user_data["persona_prompt"]
    history_list = user_data["history"]
    love_score = user_data["love_score"]
    char_name = user_data["name"]

    # 1) 사용자 메시지 기록
    history_list.append(f"User:{user_input}")

    # 2) system_prompt 구성
    system_prompt = (
        env_prompt.replace("{user_name}",user_name)
        + "\n"
        + persona_prompt
        + "\n현재 호감도: "
        + str(love_score)
        + "\n호감도 해석: "
        + get_love_description(love_score)
        + "\n이건 과거 대화의 요약이야:"
        + chat_history_sum(history_list)
        + "\n과거 채팅들이야:"
        + last_messages(history_list)
        + f"\n채팅 수:{len(history_list)}\n"
    )

    # 3) Gemini 호출 -> 메인 응답 (LLM)
    raw_ans = call_gemini_api(user_input, system_prompt)
    # 4) JSON 파싱 -> reply, score
    try:
        response_text, score = parse_json_braces(raw_ans)
    except:
        response_text = "이해하지 못했습니다."
        score = 0

    # 호감도 업데이트
    if love_score >= 50 and score > 0:
        score = score // 2
    love_score += score
    if love_score > 100:
        love_score = 100
    user_data["love_score"] = love_score

    # 봇 메시지 기록
    history_list.append(f"{char_name}:{response_text}")

    # ---------------------------
    # (5) 추가: 추천 대답 3개 생성
    # ---------------------------
    # 최근 봇 메시지에 대한 3가지 응답 제안
    # 맥락(최근 대화) + "방금 이연희가 이렇게 말했다" -> 3개 제안
    # 응답 포맷: {"대답1":"...", "대답2":"...", "대답3":"..."}
    recommend_prompt = (
        "다음은 방금 상대방이 한 말입니다.\n"
        f"'{response_text}'\n"
        "다음은 현재까지의 대화 요약입니다.\n"
        + chat_history_sum(history_list) +
        "여기에 대해 당신이 할 수 있는 짧은 대답 3가지를 만들어 주세요. "
        "응답 형식은 반드시 {\"대답1\":\"...\", \"대답2\":\"...\", \"대답3\":\"...\"} 이고 "
        "그 외 어떠한 내용도 포함하지 말아 주세요."
        "당신이 생성하는 대답은 상대에게 호감을 살 수도 있고 상대의 기분을 나쁘게 만들 수도 있습니다."
        "이것은 가상의 소개팅 시나리오입니다. 당신은 지인에게 상대방을 소개받았고, "
        "상대방을 지금 처음 만나서 1:1데이트를 하게 된 상황입니다."
        f"상대방 이름: {char_name}, 당신의 이름: {user_name}"
    )
    raw_reco = call_gemini_api(" ", recommend_prompt)
    recommended_dict = parse_recommended_answers(raw_reco)
    # 예시: {"대답1":"...", "대답2":"...", "대답3":"..."}
    if not recommended_dict:
        recommended_dict = {"대답1":"추천된 응답이 없습니다.", "대답2":"추천된 응답이 없습니다.", "대답3":"추천된 응답이 없습니다."}

    return jsonify({
        "reply": response_text,
        "score": score,
        "current_love_score": love_score,
        "recommended_answers": recommended_dict
    })





@app.route("/all_scores")
def all_scores():
    """
    모든 캐릭터들의 현재 호감도를 반환
    """
    result = {}
    for user_id, data in users_data.items():
        result[user_id] = {
            "name": data["name"],
            "love_score": data["love_score"]
        }
    comment = get_final_result(result)
    for user_id in users_data:
        users_data[user_id]["history"] = []
        users_data[user_id]["love_score"] = 0
    print(users_data)
    return jsonify({"status":"ok", "scores":result, "comment":comment})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
```

