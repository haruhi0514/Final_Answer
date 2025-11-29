"a[href^='https://r.gnavi.co.jp/'][data-id]")


    for s in shops:
        link = s.get("href")
        if link and link.startswith("https://r.gnavi.co.jp/"):
            shop_links.append(link)
        if len(shop_links) >= 50:
            break  # 店舗リンク50件で内側ループ終了

    if len(shop_links) >= 50:
        break  # ページループも終了

    time.sleep(1)  # 次ページ取得まで1秒待機

print(f"取得した店舗リンク数: {len(shop_links)}")

records = []  # 全角スペースを削除

# 住所正規表現
addr_pattern = re.compile(r"(東京都|北海道|(?:大阪|京都|兵庫)府|.{2,3}県)(.+?市|.+?区|.+?町|.+?村)(.*)")

for link in shop_links:
    res = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    # 店名
  # 住所（addressタグも含めて取得）
address_tag = soup.select_one("p.address, p.region, span.region")
prefecture = city = address_num = building = ""

if address_tag:
    address = address_tag.text.strip()
    m = addr_pattern.search(address)
    if m:
        prefecture = m.group(1)
        city = m.group(2)
        rest = m.group(3).strip()
        if " " in rest:
            parts = rest.split(" ", 1)
            address_num = parts[0]
            building = parts[1]
        else:
            address_num = rest


    # 電話番号
    tel_tag = soup.select_one("span.number")
    tel = tel_tag.text.strip() if tel_tag else ""

    # メールアドレス（ない場合は空欄）
    email = ""

    # 住所
    address_tag = soup.select_one("p.region, span.region")
    prefecture = city = address_num = building = ""

    if address_tag:
        address = address_tag.text.strip()
        m = addr_pattern.search(address)
        if m:
            prefecture = m.group(1)
            city = m.group(2)
            rest = m.group(3).strip()
            if " " in rest:
                parts = rest.split(" ", 1)
                address_num = parts[0]
                building = parts[1]
            else:
                address_num = rest

    # 店舗URL
    homepage = link

    # SSLは空欄
    ssl = ""

    records.append([name, tel, email, prefecture, city, address_num, building, homepage, ssl])
    time.sleep(1)

# DataFrame作成
df = pd.DataFrame(records, columns=[
    "店舗名", "電話番号", "メールアドレス",
    "都道府県", "市区町村", "番地", "建物名",
    "URL", "SSL"
])

# CSV出力
df.to_csv("1-1_sjis.csv", index=False, encoding="cp932")
print("✅ 1-1.csv を作成しました。提出できます。")




import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# ぐるなび 店舗一覧ページ（全国）
list_url = "https://r.gnavi.co.jp/area/jp/rs/?p={}"

shop_links = []

# 50店舗集める
for page in range(1, 20):
    res = requests.get(list_url.format(page), headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    # HTMLを保存して確認
    with open(f"page_{page}.html", "w", encoding="utf-8") as f:
        f.write(res.text)
    print(f"✅ page_{page}.html を保存しました")

    # 店舗リンク取得
    shops = soup.select(