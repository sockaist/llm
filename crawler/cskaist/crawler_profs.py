import requests
from bs4 import BeautifulSoup
import re
import json
import time

BASE_DOMAIN = "https://cs.kaist.ac.kr"

def get_professor_urls():
    url = f"{BASE_DOMAIN}/people/faculty"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    urls = []
    for item in soup.select('ul.item_box li.horiz_item div.item.fix'):
        onclick = item.get('onclick', '')
        m = re.search(r'facultyView\((\d+),\s*(\d+)\)', onclick)
        if m:
            idx, menu = m.groups()
            link = f"{BASE_DOMAIN}/people/view?idx={idx}&kind=faculty&menu={menu}"
            urls.append(link)
    return urls

def parse_professor(url):
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    info = {
        "name":   "",
        "field":  "",
        "major":  "",
        "degree": "",
        "web":    "",
        "mail":   "",
        "phone":  "",
        "office": "",
        "etc":    "",
        "tag":    "csweb.profs"
    }

    # 이름
    h3 = soup.select_one('div.inner h3')
    info["name"] = h3.get_text(strip=True) if h3 else ""

    dl = soup.select_one('dl.detail')
    etc_parts = []
    if dl:
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            key = dt.get_text(strip=True)
            val = dd.get_text(strip=True)

            if key == "연구분야":
                info["field"] = val
            elif key == "전공":
                info["major"] = val
            elif key == "학위":
                info["degree"] = val
            elif key == "웹사이트":
                a = dd.select_one('a[href]')
                href = a['href'].strip() if a else val
                info["web"] = href if href.startswith("http") else BASE_DOMAIN + href
            elif key == "이메일":
                a = dd.select_one('a[href^="javascript:emailSend"]')
                if a:
                    href = a['href']
                    m = re.search(r"emailSend\('([^']+)'\)", href)
                    if m:
                        email = m.group(1).replace('^*', '@')
                        info["mail"] = email
                    else:
                        info["mail"] = val.replace("(at)", "@").replace(" ", "")
                else:
                    # 만약 a태그가 없으면 텍스트로 시도
                    info["mail"] = val.replace("(at)", "@").replace(" ", "")
            elif key == "전화번호":
                info["phone"] = val
            elif key == "교수연구실":
                info["office"] = val
            else:
                etc_parts.append(f"{key}: {val}")

    bio = soup.select_one('div.detailTXt')
    if bio:
        text = bio.get_text("\n", strip=True)
        if text:
            etc_parts.append(text)

    info["etc"] = "\n\n".join(etc_parts)
    return info

def crawl_all(delay=0.1):
    profs = []
    for url in get_professor_urls():
        try:
            prof = parse_professor(url)
            profs.append(prof)
        except Exception as e:
            print(f"Error parsing {url}: {e}")
        time.sleep(delay)
    return profs

from csweb_save import save_items
def crawler_profs():
    data = crawl_all()
    save_items(data, res_dir="res")    # ← 단 두 줄만 교체
    print(f"{len(data)} items stored in res for csweb.profs/")

if __name__ == "__main__":
    crawler_profs()
