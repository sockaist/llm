import requests
from bs4 import BeautifulSoup
import re
import json
import time

BASE_DOMAIN = "https://cs.kaist.ac.kr"
LIST_URL    = f"{BASE_DOMAIN}/resources/"

def crawl_seminar_rooms(i, delay=0.1):
    """
    세미나실 목록 페이지에서 각 방의 예약 버튼을 찾아
    roomnum, 이름, 설비 정보를 한 번에 파싱합니다.
    """
    resp = requests.get(LIST_URL + i)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    rooms = []
    for div in soup.select('div.item2.fix'):  # refer.html 구조 :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}
        # 1) 예약 URL 파라미터(roomnum) 추출
        a_reserve = div.select_one('p.reserve a[href^="javascript:reservationRoom"]')
        if not a_reserve:
            continue
        m = re.search(r'reservationRoom\((\d+)\)', a_reserve['href'])
        if not m:
            continue
        room_sno = m.group(1)

        # 2) 방 이름
        title_el = div.select_one('p.tit span')
        name = title_el.get_text(strip=True) if title_el else ""

        # 3) 설비 정보 목록(테이블수, 좌석수, 부대장치 등)
        occup_items = div.select('ul.occup li')
        etc_parts = [li.get_text(strip=True) for li in occup_items]
        etc = " ".join(etc_parts)

        # 4) 최종 예약 URL
        web = f"{LIST_URL}?mode=reserve&roomnum={room_sno}"

        rooms.append({
            "name": name,
            "web":  web,
            "etc":  etc,
            "tag":  "csweb.refer"
        })

        time.sleep(delay)

    return rooms

def crawl_all():
    data = []
    for i in ["seminarroom", "lectureroom", "meeting", "multipurpose", "welfarefacility"] :
        tmp = crawl_seminar_rooms(i)
        data += tmp

from csweb_save import save_items
def crawler_room():
    data = crawl_all()
    save_items(data, res_dir="res")
    print(f"{len(data)} items stored in res for csweb.ai for csweb.refer/")

if __name__ == "__main__":
    crawler_room()
