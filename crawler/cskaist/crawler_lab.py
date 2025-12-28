import requests
from bs4 import BeautifulSoup
import re
import json
from time import sleep

BASE_DOMAIN = "https://cs.kaist.ac.kr"

def get_listing_urls():
    """
    연구실 목록 페이지에서 labView 링크를 절대 URL로 반환
    """
    url = f"{BASE_DOMAIN}/research/labs"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    urls = []
    for a in soup.select('ul.item_box li.horiz_item a'):
        href = a.get('href', '').strip()
        if not href:
            continue
        # 절대 URL로 변환
        if href.startswith('http'):
            full_url = href
        elif href.startswith('/'):
            full_url = BASE_DOMAIN + href
        else:
            full_url = f"{BASE_DOMAIN}/{href}"
        urls.append(full_url)
    return urls

def parse_lab(url):
    """
    labView 상세 페이지에서 필요한 필드들을 파싱해 dict로 반환
    """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1) 연구실 이름
    name_el = soup.select_one('div.inner h3')
    name = name_el.get_text(strip=True) if name_el else ''

    # 2) dl.detail dd 순서대로 주요 정보 꺼내기
    dds = soup.select('dl.detail dd')
    professor = dds[0].get_text(strip=True) if len(dds) > 0 else ''
    field     = dds[1].get_text(strip=True) if len(dds) > 1 else ''
    web       = dds[2].get_text(strip=True) if len(dds) > 2 else ''

    # 3) 이메일: javascript:emailSend('minsukk^*kaist.ac.kr');
    email = ''
    if len(dds) > 3:
        email_dd = dds[3]
        a_tag = email_dd.select_one('a')
        if a_tag and 'href' in a_tag.attrs:
            href = a_tag['href']
            m = re.search(r"emailSend\('([^']+)'\)", href)
            if m:
                # '^*'을 '@'로 치환
                email = m.group(1).replace('^*', '@')
        if not email:
            # fallback: 텍스트에서 '(at)' 치환
            text = email_dd.get_text(strip=True)
            email = re.sub(r"\s*\(at\)\s*", "@", text)

    # 4) 전화번호
    phone  = dds[4].get_text(strip=True) if len(dds) > 4 else ''
    # 5) 사무실 위치
    office = dds[5].get_text(strip=True) if len(dds) > 5 else ''

    # 6) 소개자료(intro): dd[6] 안의 <a> href
    intro = ''
    if len(dds) > 6:
        a_intro = dds[6].select_one('a')
        if a_intro and a_intro.get('href'):
            href = a_intro['href'].strip()
            if href.startswith('http'):
                intro = href
            elif href.startswith('/'):
                intro = BASE_DOMAIN + href
            else:
                intro = f"{BASE_DOMAIN}/{href}"

    # 7) 설명글(etc): div.detailTXt 안의 p.cl_research 텍스트
    detail_txt = soup.select_one('div.detailTXt')
    etc_parts = []
    if detail_txt:
        for p in detail_txt.select('p.cl_research'):
            text = p.get_text(strip=True)
            if text:
                etc_parts.append(text)
    etc = '\n\n'.join(etc_parts)

    return {
        "name":      name,
        "professor": professor,
        "field":     field,
        "web":       web,
        "email":     email,
        "phone":     phone,
        "office":    office,
        "intro":     intro,
        "etc":       etc,
        "tag":       "csweb.research"
    }

def crawl_all(delay=0.3):
    labs = []
    for url in get_listing_urls():
        try:
            lab_info = parse_lab(url)
            labs.append(lab_info)
        except Exception as e:
            print(f"Error parsing {url}: {e}")
        sleep(delay)
    return labs

from csweb_save import save_items
def crawler_lab():
    data = crawl_all()
    save_items(data, res_dir="res")    # ← 단 두 줄만 교체
    print(f"{len(data)} items stored in res for csweb.research/")

if __name__ == "__main__":
    crawler_lab()
