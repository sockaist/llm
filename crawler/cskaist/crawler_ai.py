import requests
from bs4 import BeautifulSoup
import re
import json
from time import sleep

def get_listing_urls(page=1):
    """
    하나의 목록 페이지에서 각 공지의 상세 링크를 추출
    """
    url = "https://cs.kaist.ac.kr/bbs/airesearch"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    urls = []
    for item in soup.select('ul.item_box li.verti_item div.item'):
        onclick = item.get('onclick', '')
        params = re.findall(r"'([^']*)'", onclick)
        if len(params) >= 6:
            bbs_id, bbs_sn, page_no, skey, svalue, menu = params[:6]
            link = (
                f"https://cs.kaist.ac.kr/board/view"
                f"?bbs_id={bbs_id}&bbs_sn={bbs_sn}"
                f"&page={page_no}&skey={skey}&svalue={svalue}&menu={menu}"
            )
            urls.append(link)
    return urls

def parse_article(url):
    """
    상세 페이지에서 제목, 날짜(문자열), 본문을 파싱해서 반환
    """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1) 제목
    title_el = soup.select_one('div.inner h3')
    title = title_el.get_text(strip=True) if title_el else ''

    # 2) 날짜: div.inner p.dept 텍스트 추출 후 포맷팅
    date_el = soup.select_one('div.inner p.dept')
    if date_el:
        # 예: "2025.05.10" 또는 "2025.05.10 17:30"
        raw = date_el.get_text(strip=True)
        # 시간 정보가 없으면 00:00:00을, 있으면 시분 뒷부분만 붙이기
        parts = raw.split()
        if len(parts) == 1:
            date = parts[0] + " 00:00:00"
        else:
            # 예: ["2025.05.10", "17:30"]
            date = parts[0] + " " + parts[1] + ":00"
    else:
        date = "0000.00.00 00:00:00"

    # 3) 본문
    content_div = soup.select_one('div.inner div.detailTxt')
    content = content_div.get_text('\n', strip=True) if content_div else ''

    return title, date, content

def crawl_all(delay=0.1):
    """
    공지 목록에서 링크를 뽑아 parse_article을 돌리고 결과를 반환
    """
    results = []
    for link in get_listing_urls():
        try:
            title, date, content = parse_article(link)
            results.append({
                "title":   title,
                "date":    date,
                "link":    link,
                "content": content,
                "tag":     "csweb.ai"
            })
        except Exception as e:
            print(f"[Error] {link} 파싱 실패:", e)
        sleep(delay)
    return results

from csweb_save import save_items
def crawler_ai():
    data = crawl_all()
    save_items(data, res_dir="res")
    print(f"{len(data)} items stored in res for csweb.ai/")

if __name__ == "__main__":
    crawler_ai()
