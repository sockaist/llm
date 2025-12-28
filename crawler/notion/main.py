from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import os
import re

options = Options()
options.add_argument("--start-maximized")  # 전체화면
# options.add_argument("headless")

driver = webdriver.Chrome(options=options)

def get_urls(url, save_path, tag):
    def get_posts():  # 현재 페이지에 보이는 공지글 list
        # 새로고침 할 때마다 바뀜
        selector = "#notion-app > div > div:nth-child(1) > div > div:nth-child(1) > main > div > div > div:nth-child(4) > div:nth-child(2) > div > div > div > div.notion-selectable.notion-collection_view_page-block > div > div:nth-child(2) > div:nth-child(2)"
        links_ele = driver.find_elements(By.CSS_SELECTOR, selector)[0]

        # 스크롤 해야함
        childs = links_ele.find_elements(By.XPATH, "./div")
        return childs

    def scroll_bottom():
        # 스크롤을 맨 아래로 내리기
        actions = ActionChains(driver)
        body = driver.find_element(By.TAG_NAME, 'body')
        actions.move_to_element(body)
        actions.click()
        for i in range(10):
            actions.send_keys(Keys.END).perform()
            time.sleep(0.3)
    
    def scroll_up():
        # 위로 스크롤
        actions = ActionChains(driver)
        body = driver.find_element(By.TAG_NAME, 'body')
        driver.execute_script("document.body.style.zoom='200%'")
        time.sleep(0.1)
        actions.move_to_element(body)
        actions.key_down(Keys.SHIFT).send_keys(Keys.SPACE).key_up(Keys.SHIFT).perform()
        time.sleep(0.1)
        driver.execute_script("document.body.style.zoom='100%'")
        time.sleep(0.1)

    with open(save_path, "r", encoding='utf-8') as f:
        save_data = json.load(f)

    # print("save data : ", save_data)

    save_id = [item["id"] for item in save_data]
    save_title = [item["title"] for item in save_data]  # 필요 없을수도

    # urls = []

    driver.get(url)
    time.sleep(5)

    scroll_bottom()  # 스크롤을 맨 아래로 내리기
    time.sleep(1)

    # 글 개수 확인
    childs = get_posts()
    last_index = int(childs[-1].get_attribute('data-index')) # 마지막 글의 data-index 확인 -> 개수 확인

    print("last index : ", last_index)


    # url 크롤링
    for i in range(last_index, -1, -1):
    # for i in range(100, -1, -1): # debugging용
        # i : data-index
        # id : 가장 아래 글이 0, 최근 글이 -1

        id = last_index - i
        print(f"id {id} 글 크롤링 시작")

        # id 중복 확인
        if id in save_id:
            print("이미 크롤링된 데이터")
            continue  # 이미 크롤링한 글은 건너뛰기
    
        # 스크롤을 맨 아래로 내리기
        scroll_bottom()
        time.sleep(0.5)

        while True:
            # 현재 페이지에 보이는 공지글 list
            childs = get_posts()
            start_index = int(childs[0].get_attribute('data-index'))
            final_index = int(childs[-1].get_attribute('data-index'))

            # if i >= start_index and i <= final_index:
            #     break

            if (i-start_index > 12 and i <= final_index) or start_index == 0:
                break

            scroll_up()
            # print("스크롤 올리기")

        # 85 (12) 97 (21) 118 (12) 130
        # 121 (12) 133 ( ) 148 (0) 148
        

        # index가 i인 글
        child = childs[i-start_index]
        # id = last_index - int(child.get_attribute('data-index'))
        # print(id, " 글 크롤링 시작")

        title = child.text.split('\n')[0]

        # url 크롤링 시작
        hover_element = child.find_element(By.XPATH, "./div/div[1]/div/div[2]")


        actions = ActionChains(driver)
        actions.move_to_element(hover_element)
        actions.click().perform()

        into_button = hover_element.find_element(By.CLASS_NAME, 'quickActionContainer')
        into_button.click()

        if tag == "marketing":
            selector = r'#notion-app > div > div:nth-child(1) > div > div.notion-peek\-renderer > div > div:nth-child(2) > div > div:nth-child(1) > div:nth\-child(1) > div:nth-child(2) > div > a'
            detail_button = driver.find_element(By.CSS_SELECTOR, selector)

        
            link = detail_button.get_attribute("href")

        elif tag == "notice":
            link = driver.current_url
        
        else:
            continue  # 잘못된 태그 처리
        
        # 새 형식으로 데이터 추가
        save_data.append({"id": id, "title": title, "url": link})
        save_title.append(title)  # 제목 리스트에도 추가
        save_id.append(id)  # 제목 리스트에도 추가
        print(f"id: {id}, 제목: {title}, 링크: {link}")

        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        driver.back()

        time.sleep(2)

    return save_data


def clean_filename(filename):
    # 윈도우에서 파일명으로 사용할 수 없는 문자: \ / : * ? " < > |
    # 다른 운영체제에서도 문제가 될 수 있는 문자 포함
    invalid_chars = r'[\\/*?:"<>|]'
    
    # 정규식을 사용하여 금지된 문자를 공백으로 대체
    cleaned_name = re.sub(invalid_chars, ' ', filename)
    
    return cleaned_name

def get_data(page_url):
    driver.get(page_url)
    time.sleep(5)

    data = {}

    title_element = driver.find_elements(By.TAG_NAME, "h1")[0]
    title = title_element.text
    data["title"] = title

    date_element = driver.find_elements(By.CSS_SELECTOR, "#notion-app > div > div:nth-child(1) > div > div:nth-child(1) > main > div > div > div.whenContentEditable > div > div.layout-content.layout-content-with-divider > div > div")[0]
    date = date_element.text
    date = date.split("\n")
    start = date[1]
    finish = date[3]
    data["start"] = start
    data["finish"] = finish

    contents_element = driver.find_elements(By.CLASS_NAME, "notion-page-content")[0]
    contents = contents_element.text

    images = contents_element.find_elements(By.TAG_NAME, "img")
    images_uri = []
    for image in images:
        uri = image.get_attribute("src")
        if "https://kaist-cs.notion.site/image/" in uri:
            images_uri.append(uri)

    data["contents"] = contents
    data["images"] = images_uri

    data["url"] = page_url

    # print("Title:", title)
    # print("Start Date:", start)
    # print("Finish Date:", finish)
    # print("Contents:", contents)
    # print("Images:", images_uri)
    # print(data)

    return data


if __name__ == "__main__":
    data_path = "./notion_data/"
    
    #############
    # url 크롤링 #
    #############
    
    # 공지글 크롤링
    url = "https://www.notion.so/kaist-cs/35fd4f77ceed4f658d2fb0294023375d?v=4bee22a0f4b041c8a55fa0826151007b"
    notice_path = data_path+"notice.json"
    datas = get_urls(url, notice_path, tag="notice")
    
    # 외부 홍보글 크롤링
    url = "https://www.notion.so/kaist-cs/d010283314f2458faeb4960a1a28bb41?v=83dc21c1a9b445b989c2504724f52dc9"
    marketing_path = data_path+"marketing.json"
    datas = get_urls(url, marketing_path, tag="marketing")
    
    print("url 크롤링 완료")


    ################
    # 개별 글 크롤링 #
    ################

    # notice 글 크롤링
    with open(notice_path, "r", encoding='utf-8') as f:
        save_data = json.load(f)

    for data in save_data:
        id = data["id"]
        title = data["title"]
        url = data["url"]
        
        file_name = f"{data_path}notice/post_{id}.json"
        if os.path.exists(file_name):
            print(f"{file_name} already exists. Skipping...")
            continue    
        
        print(f"Processing {title}")
        # print(f"URL: {url}")
        data = get_data(url)

        # 저장
        with open(file_name, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # marketing 글 크롤링
    with open(marketing_path, "r", encoding='utf-8') as f:
        save_data = json.load(f)
        
    for data in save_data:
        id = data["id"]
        title = data["title"]
        url = data["url"]
        
        file_name = f"{data_path}marketing/post_{id}.json"
        if os.path.exists(file_name):
            print(f"{file_name} already exists. Skipping...")
            continue    
        
        print(f"Processing {title}...")
        print(f"URL: {url}")
        data = get_data(url)

        # 저장
        with open(file_name, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print("개별 글 크롤링 완료")

driver.quit()