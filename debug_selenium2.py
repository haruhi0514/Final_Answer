from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

options = webdriver.ChromeOptions()
options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
driver = webdriver.Chrome(options=options)

url = "https://r.gnavi.co.jp/area/tokyo/kods00186/rs/"
print(f"アクセス: {url}")
driver.get(url)

print("ページ読み込み中... 10秒待機")
time.sleep(10)  # 長めに待機

print(f"ページタイトル: {driver.title}")

# スクロールしてコンテンツを読み込む
print("スクロール中...")
for i in range(3):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

# 全てのリンクを取得
all_links = driver.find_elements(By.TAG_NAME, 'a')
print(f"全リンク数: {len(all_links)}")

# 店舗らしきリンクを探す
restaurant_links = []
print("\n店舗リンクを探しています...")
for link in all_links:
    try:
        href = link.get_attribute('href')
        text = link.text
        
        if href and 'gnavi.co.jp' in href:
            # r.gnavi.co.jp/で始まり、十分に短いパス（店舗ID）
            if href.startswith('https://r.gnavi.co.jp/') and href.count('/') <= 4:
                if href not in ['https://r.gnavi.co.jp/', 'https://r.gnavi.co.jp/area/']:
                    restaurant_links.append(href)
                    print(f"  見つかった: {href} (テキスト: {text[:30]})")
    except:
        pass

print(f"\n店舗リンク候補: {len(restaurant_links)} 件")

# ユニークなリンク
unique_links = list(set(restaurant_links))
print(f"ユニークなリンク: {len(unique_links)} 件")

for link in unique_links[:10]:
    print(f"  {link}")

input("\nEnterキーを押すとブラウザを閉じます...")
driver.quit()
