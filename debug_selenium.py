from selenium import webdriver
from selenium.webdriver.common.by import By
import time

options = webdriver.ChromeOptions()
options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
driver = webdriver.Chrome(options=options)

url = "https://r.gnavi.co.jp/area/jp/rs/"
print(f"アクセス: {url}")
driver.get(url)
time.sleep(5)

# ページタイトルを確認
print(f"ページタイトル: {driver.title}")

# 全てのリンクを取得
all_links = driver.find_elements(By.TAG_NAME, 'a')
print(f"全リンク数: {len(all_links)}")

# /restaurant/ を含むリンクを探す
restaurant_links = []
for link in all_links[:50]:  # 最初の50個だけチェック
    href = link.get_attribute('href')
    if href and '/restaurant/' in href:
        restaurant_links.append(href)
        print(f"  → {href}")

print(f"\n店舗リンク数: {len(restaurant_links)}")

# HTMLをファイルに保存
with open('page_source.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
print("\nHTMLを page_source.html に保存しました")

input("Enterキーを押すとブラウザを閉じます...")
driver.quit()
