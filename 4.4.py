# 1-1.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

# ユーザーエージェント設定
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.111 Safari/537.36"
}

# ぐるなびの検索URL（例：東京・居酒屋）
BASE_URL = "https://r.gnavi.co.jp/area/jp/tokyo/rs/?page={}"

# 取得件数
TARGET_COUNT = 50

# 結果格納リスト
data_list = []

# ページごとに取得
page = 1
while len(data_list) < TARGET_COUNT:
    url = BASE_URL.format(page)
    response = requests.get(url, headers=HEADERS)
    time.sleep(3)  # サーバーに負荷をかけないために待機
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 店舗リスト取得（ぐるなびの店舗リストクラスは変更されることがあります）
    shops = soup.select("div.rstlst-cassette__item")  # 例として
    if not shops:
        break  # 店舗がなければ終了
    
    for shop in shops:
        if len(data_list) >= TARGET_COUNT:
            break
        
        # 店舗名
        name_tag = shop.select_one("a.rstlst-name")
        name = name_tag.text.strip() if name_tag else ""
        
        # 電話番号
        tel_tag = shop.select_one("span.tel")
        tel = tel_tag.text.strip() if tel_tag else ""
        
        # メールアドレスは店舗ページから取得不可 → 空欄
        email = ""
        
        # 住所取得
        address_tag = shop.select_one("li.address")
        address = address_tag.text.strip() if address_tag else ""
        
        # 正規表現で住所を分割
        prefecture = city = block = building = ""
        if address:
            # 都道府県を取得
            m = re.match(r"^(東京都|北海道|(?:京都|大阪)府|.{2,3}県)(.*)", address)
            if m:
                prefecture = m.group(1)
                rest = m.group(2)
                # 市区町村と番地・建物名
                m2 = re.match(r"^(.+?[市区町村])(.+)", rest)
                if m2:
                    city = m2.group(1)
                    block_building = m2.group(2)
                    # 番地と建物名は簡易的に分割（番地は数字＋丁目まで）
                    m3 = re.match(r"^(\d{1,3}[-丁目0-9]+)?(.*)", block_building)
                    if m3:
                        block = m3.group(1) if m3.group(1) else ""
                        building = m3.group(2) if m3.group(2) else ""
        
        # URLはrequestsでは取得不可 → 空欄
        url_official = ""
        ssl = False
        
        # リストに追加
        data_list.append({
            "店舗名": name,
            "電話番号": tel,
            "メールアドレス": email,
            "都道府県": prefecture,
            "市区町村": city,
            "番地": block,
            "建物名": building,
            "URL": url_official,
            "SSL": ssl
        })
    
    page += 1

# DataFrame作成
df = pd.DataFrame(data_list)

# CSV出力（Excel文字化け対策）
df.to_csv("1-1.csv", index=False, encoding="utf-8-sig")
print("1-1.csv を出力しました。")
