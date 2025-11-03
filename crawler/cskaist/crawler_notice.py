
    


import requests
from bs4 import BeautifulSoup
import re
import json
from time import sleep

def get_listing_urls(page):
    """
    하나의 목록 페이지에서 각 공지의 상세 링크를 추출
    """
    url = f"https://cs.kaist.ac.kr/board/list?page={page}&bbs_id=notice"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    urls = []
    # 목록 아이템 선택: onclick 속성에서 파라미터 추출
    for a in soup.select('td.line2_2_txt a'):
        href = a.get('href', '')
        # 'notice', '9005', '3', 'subject', '', '151' 등 6개 항목
        params = re.findall(r"'([^']*)'", href)
        if len(params) >= 6:
            bbs_id, bbs_sn, p, skey, svalue, menu = params[:6]
            link = (
                f"https://cs.kaist.ac.kr/board/view"
                f"?bbs_id={bbs_id}&bbs_sn={bbs_sn}"
                f"&page={p}&skey={skey}&svalue={svalue}&menu={menu}"
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

    # —– 수정된 날짜 파싱 부분 —–
    date      = "0000-00-00 00:00:00"
    date_tag  = None

    date_list = soup.select_one('ul.employInfo')
    if date_list:
        for li in date_list.select('li'):
            strong = li.select_one('strong')
            if strong and strong.get_text(strip=True) == "Post Date":
                raw = li.get_text(strip=True)
                date_tag = raw.replace("Post Date", "", 1).strip()
                break

    if date_tag:
        date = date_tag.split()[0] + " 00:00:00"

    # 3) 본문 선택자도 select_one() 사용
    content_div = soup.select_one('div.textBox div.viewDetail')
    content = content_div.get_text(' ', strip=True) if content_div else ''

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
            print(f"  크롤링을 종료합니다.")
            return all_results

        for link in urls:
            try:
                title, date, content = parse_article(link)
                all_results.append({
                    "title":   title,
                    "date":    date,
                    "link":    link,
                    "content": content,
                    "tag":     "csweb.notice"
                })
            except Exception as e:
                print(f"    [Error] 상세 페이지 파싱 실패 ({link}): {e}")
            sleep(delay)  # 서버 부하를 줄이기 위해 잠시 대기

    return all_results

from csweb_save import save_items
def crawler_notice():
    data = crawl_all()
    save_items(data, res_dir="res")    # ← 단 두 줄만 교체
    print(f"{len(data)} items stored in res for csweb.notice/")

if __name__ == "__main__":
    crawler_notice()

