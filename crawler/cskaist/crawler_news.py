
    


import requests
from bs4 import BeautifulSoup
import re
import json
from time import sleep

def get_listing_urls(page):
    """
    하나의 목록 페이지에서 각 공지의 상세 링크를 추출
    """
    url = f"https://cs.kaist.ac.kr/board/list?page={page}&bbs_id=news"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    urls = []
    # 목록 아이템 선택: onclick 속성에서 파라미터 추출
    for item in soup.select('ul.item_box li.verti_item div.item'):
        onclick = item.get('onclick', '')
        params = re.findall(r"'([^']*)'", onclick)
        if len(params) >= 6:
            bbs_id, bbs_sn, page_no, skey, svalue, menu = params[:6]
            link = (
                "https://cs.kaist.ac.kr/board/view"
                f"?bbs_id={bbs_id}&bbs_sn={bbs_sn}"
                f"&page={page_no}&skey={skey}&svalue={svalue}&menu={menu}"
            )
            urls.append(link)
    return urls

def parse_article(url):
    """
    상세 페이지에서 제목, 날짜, 본문을 파싱해서 반환
    (사이트 구조에 맞춰 selector를 조정하세요)
    """
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1) 제목 선택자: 예시로 .view_top h3 사용
    title_tag = soup.select_one('div.inner h3')  
    title = title_tag.get_text(strip=True) if title_tag else ''

    # 2) 날짜 선택자: 예시로 .view_top span.date 사용
    date_tag = soup.select_one('div.inner p.dept')
    if date_tag:
        raw = date_tag.get_text(strip=True)
        # "2025.05.10" → "2025.05.10 00:00:00"
        date = raw.split()[0] + " 00:00:00"
    else:
        date = "0000-00-00 00:00:00"

    # 3) 본문 선택자: 예시로 #view_content 사용
    content_div = soup.select_one('div.inner div.detailTxt')
    content = content_div.get_text('\n', strip=True) if content_div else ''

    return title, date, content

def crawl_all(max_page=25, delay=0.05):
    """
    1페이지부터 max_page까지 순회하며 크롤링
    """
    all_results = []
    for pg in range(1, max_page+1):
        print(f"Crawling listing page {pg}...")
        try:
            urls = get_listing_urls(pg)
        except Exception as e:
            print(f"  [Error] 페이지 {pg} 크롤 실패: {e}")
            continue

        if not urls:
            print(f"  페이지 {pg}에서 공지를 찾을 수 없습니다.")
            continue

        for link in urls:
            try:
                title, date, content = parse_article(link)
                all_results.append({
                    "title":   title,
                    "date":    date,
                    "link":    link,
                    "content": content,
                    "tag":     "csweb.news"
                })
            except Exception as e:
                print(f"    [Error] 상세 페이지 파싱 실패 ({link}): {e}")
            sleep(delay)  # 서버 부하를 줄이기 위해 잠시 대기

    return all_results

from csweb_save import save_items
def crawler_news():
    data = crawl_all()
    save_items(data, res_dir="res")    # ← 단 두 줄만 교체
    print(f"{len(data)} items stored in res for csweb.news/")

if __name__ == "__main__":
    crawler_news()
