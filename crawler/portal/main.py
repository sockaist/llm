# import json
# import time
# import argparse
#
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.action_chains import ActionChains
#
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
#
# url = "https://portal.kaist.ac.kr/kaist/portal/board/ntc/33"
# post_count = 140
#
# options = Options()
# driver = webdriver.Chrome(options=options)
#
#
# def main(kaist_id):
#     driver.get("https://portal.kaist.ac.kr")
#
#     time.sleep(3)
#
#     wait = WebDriverWait(driver, 10)
#
#     def click(by, value: str):
#         wait.until(EC.presence_of_element_located((by, value))).click()
#         time.sleep(0.5)
#
#     def send_key(by, value, text):
#         wait.until(EC.presence_of_element_located((by, value))).send_keys(text)
#         time.sleep(0.5)
#
#     def get_text(by, value):
#         return wait.until(EC.presence_of_element_located((by, value))).text
#
#     click(By.ID, "btn-sso-login")
#     send_key(By.ID, "login_id_mfa", kaist_id)
#     click(By.CLASS_NAME, "btn_login")
#
#     time.sleep(15)
#
#     click(By.CLASS_NAME, "bg_dgray")
#     driver.get(url)
#
#     time.sleep(3)
#     click(By.CSS_SELECTOR, "#postList > tr:nth-child(1) > td.text-start.td-link > div > div > a.nav-link.link-dark.my-auto.p-0.pe-1.text-truncate")
#
#     for i in range(post_count):
#         print(f'post {i} crawling...')
#         # time.sleep(5)
#         while True:
#             try:
#                 title = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-header > div.d-flex.justify-content-between.align-items-center > h3")
#                 author = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-header > div.dv-tbl-detail-info > dl:nth-child(1) > dd")
#                 date = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-header > div.dv-tbl-detail-info > dl:nth-child(2) > dd")
#                 content = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-main > pre")
#
#                 click(By.CSS_SELECTOR, "body > main > section > article.art-sub-header > div > div > a")
#                 _link = wait.until(EC.presence_of_element_located((By.ID, "copyUrl"))).get_attribute('outerHTML').strip()
#                 click(By.ID, "optCloseBtn")
#                 link = _link.split('data-clipboard-text="')[1].split('"')[0]
#                 print(link)
#
#                 with open(f'data/job/post_{i}.json', 'w', encoding='UTF-8', newline='') as f:
#                     f.write(json.dumps({
#                         "title": title,
#                         "author": author,
#                         "date": date,
#                         "link": link,
#                         "content": content,
#                     }, ensure_ascii=False, indent=2))
#
#                 time.sleep(0.1)
#                 next_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#pstPn > dl:nth-child(2) > dd > a")))
#                 actions = ActionChains(driver).move_to_element(next_btn)
#                 actions.perform()
#                 next_btn.click()
#                 break
#             except Exception as e:
#                 print(f'error: {e}')
#                 continue
#
#     driver.quit()
#
#
# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--kaistId", required=True, help="KAIST ID 입력")
#     args = parser.parse_args()
#     main(args.kaistId)
#

import json
import time
import argparse
import os
from datetime import datetime as dt

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def main(kaist_id, save_path, article_id):
    now = dt.now().strftime("%Y-%m-%d---%H-%M-%S")

    url = f"https://portal.kaist.ac.kr/kaist/portal/board/ntc/{article_id}"
    post_count = 140

    options = Options()
    # 필요하면 헤드리스 모드 등 옵션 추가 가능
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    driver.get("https://portal.kaist.ac.kr")

    wait = WebDriverWait(driver, 20)

    def click(by, value: str):
        wait.until(EC.element_to_be_clickable((by, value))).click()
        time.sleep(0.5)

    def send_key(by, value, text):
        wait.until(EC.presence_of_element_located((by, value))).send_keys(text)
        time.sleep(0.5)

    def get_text(by, value):
        return wait.until(EC.presence_of_element_located((by, value))).text

    # 로그인 과정
    click(By.ID, "btn-sso-login")
    send_key(By.ID, "login_id_mfa", kaist_id)
    click(By.CLASS_NAME, "btn_login")

    time.sleep(15)

    click(By.CLASS_NAME, "bg_dgray")
    driver.get(url)

    # 로그인 후 URL이 바뀌거나 로그인 완료를 알 수 있는 요소가 나타날 때까지 대기
    # wait.until(lambda d: d.current_url != "https://portal.kaist.ac.kr"
    #            or len(d.find_elements(By.CLASS_NAME, "bg_dgray")) > 0)

    # 로그인 성공 확인 후 이동
    # driver.get(url)
    # wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#postList")))

    # 게시글 첫 번째 항목 클릭
    time.sleep(1)
    click(By.CSS_SELECTOR, "#postList > tr:nth-child(1) > td.text-start.td-link > div > div > a.nav-link.link-dark.my-auto.p-0.pe-1.text-truncate")
    time.sleep(1)

    os.makedirs(save_path, exist_ok=True)

    for i in range(post_count):
        print(f'post {i} crawling...')
        while True:
            try:
                title = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-header > div.d-flex.justify-content-between.align-items-center > h3")
                author = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-header > div.dv-tbl-detail-info > dl:nth-child(1) > dd")
                date = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-header > div.dv-tbl-detail-info > dl:nth-child(2) > dd")
                content = get_text(By.CSS_SELECTOR, "#post > div > div.dv-tbl-detail-main > pre")

                click(By.CSS_SELECTOR, "body > main > section > article.art-sub-header > div > div > a")
                _link = wait.until(EC.presence_of_element_located((By.ID, "copyUrl"))).get_attribute('outerHTML').strip()
                click(By.ID, "optCloseBtn")
                link = _link.split('data-clipboard-text="')[1].split('"')[0]
                print(link)

                with open(os.path.join(save_path, f'post_{i}_{now}.json'), 'w', encoding='UTF-8', newline='') as f:
                    f.write(json.dumps({
                        "title": title,
                        "author": author,
                        "date": date,
                        "link": link,
                        "content": content,
                    }, ensure_ascii=False, indent=2))

                time.sleep(0.1)
                next_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#pstPn > dl:nth-child(2) > dd > a")))
                actions = ActionChains(driver).move_to_element(next_btn)
                actions.perform()
                next_btn.click()
                break
            except Exception as e:
                print(e)
                time.sleep(1)
                continue

    driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kaistId", required=True, help="KAIST ID 입력")
    parser.add_argument("--savePath", required=True, help="저장위치 입력 (root 기준)")
    parser.add_argument("--articleId", required=True, help="게시글 ID, ex: 33")

    args = parser.parse_args()
    main(args.kaistId, args.savePath, args.articleId)
