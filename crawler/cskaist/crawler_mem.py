import requests
from bs4 import BeautifulSoup
import re
import json
import time

BASE_DOMAIN = "https://cs.kaist.ac.kr"

def get_staff_urls():
    """
    행정팀/연구원 목록 페이지에서 staffView 콜백을 추출해
    상세 프로필 URL 목록을 반환합니다.
    """
    url = f"{BASE_DOMAIN}/people/staff"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    urls = []
    # mems.html의 .item.fix 요소에서 onclick="staffView(idx, menu)"
    for item in soup.select('ul.item_box li.horiz_item div.item.fix'):
        onclick = item.get('onclick', '')
        m = re.search(r'staffView\((\d+),\s*(\d+)\)', onclick)
        if m:
            idx, menu = m.groups()
            link = f"{BASE_DOMAIN}/people/view?idx={idx}&kind=staff&menu={menu}"
            urls.append(link)
    return urls

def parse_staff(url):
    """
    상세 프로필 페이지에서 정보를 파싱해 딕셔너리로 반환합니다.
    """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    info = {
        "name":   "",
        "position": "",
        "work":   "",
        "mail":   "",
        "phone":  "",
        "office": "",
        "etc":    "",
        "tag":    "csweb.admin"
    }

    # 1) 이름
    h3 = soup.select_one('h3')
    info["name"] = h3.get_text(strip=True) if h3 else ""

    # 2) 세부 정보 (<dl class="detail">)
    dl = soup.select_one('dl.detail')
    etc_parts = []
    if dl:
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True)
            val = dd.get_text(strip=True)

            if key.startswith("직책"):
                info["position"] = val
            elif key.startswith("담당업무"):
                info["work"] = val
            elif key == "이메일":
                # javascript:emailSend('id^*domain') 패턴
                a = dd.select_one('a[href^="javascript:emailSend"]')
                if a:
                    href = a['href']
                    m = re.search(r"emailSend\('([^']+)'\)", href)
                    if m:
                        info["mail"] = m.group(1).replace('^*', '@')
                    else:
                        info["mail"] = val.replace("(at)", "@").replace(" ", "")
                else:
                    info["mail"] = val.replace("(at)", "@").replace(" ", "")
            elif key == "전화번호":
                info["phone"] = val
            elif key.startswith("사무실"):
                info["office"] = val
            else:
                etc_parts.append(f"{key}: {val}")

    # 3) 추가 설명 (div.detailTXt)
    bio = soup.select_one('div.detailTXt')
    if bio:
        text = bio.get_text("\n", strip=True)
        if text:
            etc_parts.append(text)

    info["etc"] = "\n\n".join(etc_parts)
    return info

def crawl_all(delay=0.1):
    """
    모든 직원 프로필을 순회하며 크롤링한 후 리스트로 반환합니다.
    """
    staff_list = []
    for url in get_staff_urls():
        try:
            staff = parse_staff(url)
            staff_list.append(staff)
        except Exception as e:
            print(f"Error parsing {url}: {e}")
        time.sleep(delay)
    return staff_list

from csweb_save import save_items
def crawler_mem():
    data = crawl_all()
    save_items(data, res_dir="res")    # ← 단 두 줄만 교체
    print(f"{len(data)} items stored in res for csweb.admin/")

if __name__ == "__main__":
    crawler_mem()
