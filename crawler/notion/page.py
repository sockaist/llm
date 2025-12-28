# 단일 페이지 크롤링

# selenium의 webdriver를 사용하기 위한 import
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import os
import re

options = Options()
# options.add_argument("--start-maximized")  # 전체화면
options.add_argument("headless")

driver = webdriver.Chrome(options=options)

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
    # notice 글 크롤링
    save_path = "./notion_data/notice.json"
    with open(save_path, "r", encoding='utf-8') as f:
        save_data = json.load(f)

    for data in save_data:
        id = data["id"]
        title = data["title"]
        url = data["url"]
        
        file_name = f"./notion_data/notice/post_{id}.json"
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
    save_path = "./notion_data/marketing.json"
    with open(save_path, "r", encoding='utf-8') as f:
        save_data = json.load(f)
        
    for data in save_data:
        id = data["id"]
        title = data["title"]
        url = data["url"]
        
        file_name = f"./notion_data/marketing/post_{id}.json"
        if os.path.exists(file_name):
            print(f"{file_name} already exists. Skipping...")
            continue    
        
        print(f"Processing {title}...")
        print(f"URL: {url}")
        data = get_data(url)

        # 저장
        with open(file_name, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
driver.quit()