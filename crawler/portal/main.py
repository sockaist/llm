import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------
# edit here
kaistId = 'seohokim'
url = "https://portal.kaist.ac.kr/kaist/portal/board/ntc/33"
postCount = 140
# ----------

options = Options()
driver = webdriver.Chrome(options=options)

driver.get("https://portal.kaist.ac.kr")

time.sleep(3)

wait = WebDriverWait(driver, 10)


def click(by, value):
    wait.until(EC.presence_of_element_located((by, value))).click()
    time.sleep(0.5)


def send_key(by, value, text):
    wait.until(EC.presence_of_element_located((by, value))).send_keys(text)
    time.sleep(0.5)


def get_text(by, value):
    return wait.until(EC.presence_of_element_located((by, value))).text


click(By.ID, "btn-sso-login")
send_key(By.ID, "login_id_mfa", kaistId)
click(By.CLASS_NAME, "btn_login")

time.sleep(15)

click(By.CLASS_NAME, "bg_dgray")
driver.get(url)

time.sleep(3)
click(By.CSS_SELECTOR, "#postList > tr:nth-child(1) > td.text-start.td-link > div > div > a.nav-link.link-dark.my-auto.p-0.pe-1.text-truncate")

for i in range(postCount):
    print(f'post {i} crawling...')
    # time.sleep(5)
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

            with open(f'data/job/post_{i}.json', 'w', encoding='UTF-8', newline='') as f:
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
        except:
            continue

driver.quit()
