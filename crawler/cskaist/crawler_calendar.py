import requests
from bs4 import BeautifulSoup
import re
import json
from time import sleep
from datetime import datetime

def get_listing_urls(year, month):
    """
    하나의 목록 페이지에서 각 공지의 상세 링크를 추출
    """
    url = f"https://cs.kaist.ac.kr/news/calendar?mode=list&year={year}&month={month}"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    urls = []
    # 목록 아이템 선택: onclick 속성에서 파라미터 추출
    for a in soup.select('div.schedule a'):
        href = a.get('href', '')
        # 'notice', '9005', '3', 'subject', '', '151' 등 6개 항목
        params = re.findall(r"'([^']*)'", href)
        if len(params) >= 6:
            bbs_id, bbs_sn, p, skey, svalue, menu = params[:6]
            link = (
                f"https://cs.kaist.ac.kr/board/view?bbs_id={bbs_id}&bbs_sn={bbs_sn}&page={p}&skey={skey}&svalue={svalue}&menu={menu}"
            )
            urls.append(link)
    return urls

def parse_article(url):
    """
    상세 페이지에서 제목, 날짜, 본문을 파싱해서 반환
    """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1) 제목 선택자: select_one()으로 단일 요소 반환
    title_el = soup.select_one('div.inner h3')
    title = title_el.get_text(strip=True) if title_el else ''

    raw = soup.select_one('p.seminarsInfo strong')
    txt = raw.get_text()
    try:
        date, t = txt.split("@")
        date = date.strip() ; t = t.strip()
        dt = datetime.strptime(date, "%a, %b %d, %Y")

        t = t.split("~")
        time = t[0]
        hs,ms = map(int, time.split(":"))
        time = dt.replace(hour=hs, minute=ms).strftime("%Y-%m-%d %H:%M:%S")
    except: time = "0000-00-00 00:00:00"
    # 3) 본문 선택자도 select_one() 사용
    content_div = soup.select_one('div.textBox div.viewDetail')
    content = content_div.get_text(' ', strip=True) if content_div else ''

    # 4) location
    location_p = soup.select_one("div.textBox p:last-child strong")

    try: location = location_p.get_text(strip=True).replace("Location:", "")
    except Exception as e: print (f"ERROR : {e}")

    return title, time, content, location


def crawl_all(delay=0.05):
    """
    1페이지부터 max_page까지 순회하며 크롤링
    """
    all_results = []
    for year in range(2020, 2026):
        for month in range(1,13):
            print(f"Crawling listing page {year}, {month}...")
            try:
                urls = get_listing_urls(year, month)
            except Exception as e:
                print(f"  [Error] 페이지 {year}, {month} 크롤 실패: {e}")
                continue

            if not urls:
                print(f"  페이지 {year}, {month}에서 공지를 찾을 수 없습니다.")
                continue

            for link in urls:
                try:
                    title, time, content, location = parse_article(link)
                    all_results.append({
                        "title":   title,
                        "date":    time,
                        "link":    link,
                        "content": content,
                        "location":location,
                        "tag":     "csweb.calendar"
                    })
                except Exception as e:
                    print(f"    [Error] 상세 페이지 파싱 실패 ({link}): {e}")
                sleep(delay)  # 서버 부하를 줄이기 위해 잠시 대기

    return all_results

from csweb_save import save_items
def crawler_calendar():
    data = crawl_all()
    save_items(data, res_dir="res")
    print(f"{len(data)} items stored in res for csweb.ai/")

if __name__ == "__main__":
    crawler_calendar()