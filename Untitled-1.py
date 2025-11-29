#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題1-1: requests + BeautifulSoup でぐるなびの店舗一覧と店舗ページをスクレイピングして
sampleフォーマットのCSVを作成するスクリプト
出力: 1-1.csv
注意: (課題の追記に伴い) requests では店舗ページ内の「お店のホームページ(URL)」が取得できない事があるため、
      デフォルトでは URL 列は空欄になるようにしています（後述）。
"""

import time
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
from requests.exceptions import SSLError, RequestException
# === スクレイピングを始める検索結果ページURL ===
START_SEARCH_URL = "https://r.gnavi.co.jp/area/tokyo/izakaya/rs/"

# === ユーザーエージェントを設定 ===
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


# ---------------------------
# 設定（必要に応じて変更）

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": USER_AGENT}
MAX_RECORDS = 50
OUTPUT_CSV = "1-1.csv"
IDLE_SECONDS = 3  # 要求されているアイドリングタイム
# requests 版では URL を空にしてよい（課題注記） -> True にすると空欄にする
FORCE_EMPTY_URL_FOR_REQUESTS = True
# ---------------------------

# 都道府県パターン（正規表現用）
PREFS = [
    "北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県",
    "埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県",
    "岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県",
    "鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県",
    "佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"
]
PREF_PATTERN = "(" + "|".join(PREFS) + ")"

def idle():
    time.sleep(IDLE_SECONDS)

def check_ssl(url):
    """与えられたURLのSSL（https）検査。httpsならTrue, httpならFalse。例外時はFalseを返す。"""
    if not url:
        return False
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme != "https":
        return False
    try:
        # サーバーに負荷かけないようにHEADをまず試す
        resp = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        # ここまで到達すれば SSL（https）での接続に成功したと判断
        return True
    except SSLError:
        return False
    except RequestException:
        # 接続不可等は False
        return False

def split_address(address):
    """
    住所文字列を都道府県・市区町村・番地（建物名は別で取れなければ空）に分割する簡易実装。
    ロジック:
      1) 都道府県を正規表現で抽出
      2) 都道府県以降を残し、最初の数字(番地の開始)で区切って市区町村と番地を分離
    完璧ではないが課題要件を満たす程度の分割を行う。
    """
    if not address:
        return "", "", "", ""
    address = address.strip()
    m = re.match(rf"^{PREF_PATTERN}", address)
    if not m:
        # 都道府県が見つからない場合は全体を市区町村扱い
        return "", address, "", ""
    pref = m.group(0)
    rest = address[len(pref):].strip()
    # 番地は数字（全角/半角）で始まることが多いので最初の数字位置で分割
    num_match = re.search(r"[0-90-９-９]", rest)
    if num_match:
        idx = num_match.start()
        city = rest[:idx].strip()
        banchi_and_more = rest[idx:].strip()
    else:
        # 数字が無ければ city に全部入れる
        city = rest
        banchi_and_more = ""
    # 建物名は番地の後にスペースやカンマで区切られることがある -> 簡易に banchi と building を分割
    building = ""
    banchi = banchi_and_more
    # 例えば「1-2-3 ビル名」などがある場合、最初の空白以降を建物名とする
    if banchi_and_more:
        parts = re.split(r"\s+", banchi_and_more, maxsplit=1)
        if len(parts) == 2:
            banchi, building = parts[0].strip(), parts[1].strip()
    return pref, city, banchi, building

def extract_store_links_from_search(soup):
    """
    検索結果ページ（ぐるなび）から店舗ページURLを抽出する。
    ぐるなびのHTML構造は変わりやすいので、複数候補で探す実装にしています。
    """
    links = set()
    # 店舗カードのリンクっぽい要素を探す（aタグで店舗詳細に飛ぶもの）
    for a in soup.find_all("a", href=True):
        href = a['href']
        # ぐるなび内の店舗ページは /shop/ を含むことが多い（変わることあり）
        if "/shop/" in href or "/rstr/" in href or "/pub/" in href:
            links.add(urljoin("https://r.gnavi.co.jp", href))
    return list(links)

def parse_store_page(html, base_url):
    """
    店舗ページのHTMLから欲しい情報を抜き出す。
    抽出対象: 店舗名, 電話番号, メールアドレス（見つかれば）, 住所 テキスト, お店のホームページ（requests版は課題注記により取得不可の場合あり）
    """
    soup = BeautifulSoup(html, "html.parser")
    # 店舗名
    name_tag = soup.find(lambda tag: tag.name in ["h1","h2"] and ("店舗" in (tag.get("class") or []) or tag.text.strip()))
    # 汎用的にtitleやh1を参照
    name = ""
    if soup.title and soup.title.string:
        name = soup.title.string.strip()
    if not name:
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)
    # 電話番号（ハイフン有無、全角半角対応で数字を含むパターン）
    phone = ""
    phone_candidates = soup.find_all(text=re.compile(r"[0-9０-９\-\(\)（）]{6,}"))
    for txt in phone_candidates:
        t = txt.strip()
        # 簡易フィルタ: 電話っぽいパターン（市外局番を含む）
        if re.search(r"(0\d{1,4}[-ー−]?\d{1,4}[-ー−]?\d{3,4})", t):
            phone = re.search(r"(0\d{1,4}[-ー−]?\d{1,4}[-ー−]?\d{3,4})", t).group(0)
            break
    # メールアドレス
    email = ""
    mail_txt = soup.find(text=re.compile(r"[\w\.+-]+@[\w\.-]+\.\w+"))
    if mail_txt:
        m = re.search(r"[\w\.+-]+@[\w\.-]+\.\w+", mail_txt)
        if m:
            email = m.group(0)
    # 住所 - ぐるなびでは「住所」テキスト周辺にあることが多い
    address = ""
    # try: element labelled '住所' を探す
    label = soup.find(text=re.compile(r"住所"))
    if label:
        # 住所が隣接する要素に記載されている想定
        parent = label.parent
        # 兄弟要素や次の要素に住所があるか試す
        if parent:
            next_text = parent.get_text(separator=" ", strip=True)
            # 余計なラベルを除去して住所っぽい部分を抽出
            candidate = re.sub(r"住所[:：\s]*", "", next_text)
            if len(candidate) > 0 and any(pref in candidate for pref in PREFS):
                address = candidate
    if not address:
        # ページ内で都道府県キーワードを含むテキストを拾う
        all_text = soup.get_text(separator="\n", strip=True)
        for pref in PREFS:
            idx = all_text.find(pref)
            if idx != -1:
                # 行分けして、都道府県を含む行を住所候補とする
                lines = all_text.splitlines()
                for line in lines:
                    if pref in line and len(line) < 200:
                        address = line.strip()
                        break
            if address:
                break
    # お店のホームページ（requests では取得できないことがあるので、FORCE_EMPTY_URL_FOR_REQUESTS が True の場合は空）
    official_url = ""
    if not FORCE_EMPTY_URL_FOR_REQUESTS:
        # 探す場合の候補: "オフィシャルページ" や "お店のホームページ" のラベル付近の a[href]
        anchor = None
        # まずラベル検索
        for label_text in ["オフィシャルページ", "お店のホームページ", "公式サイト", "公式HP", "公式ホームページ"]:
            label_node = soup.find(text=re.compile(label_text))
            if label_node and label_node.parent:
                # 親要素中の a を探す
                a = label_node.parent.find_next("a", href=True)
                if a:
                    anchor = a
                    break
        # fallback: ページ内の外部リンクっぽい a を探す (https:// で外部へのリンク)
        if not anchor:
            for a in soup.find_all("a", href=True):
                href = a['href']
                if href.startswith("http") and "gnavi" not in href:
                    anchor = a
                    break
        if anchor:
            official_url = anchor['href'].strip()
    # 住所を分割
    pref, city, banchi, building = split_address(address)
    # 戻り値
    return {
        "店舗名": name,
        "電話番号": phone,
        "メールアドレス": email,
        "都道府県": pref,
        "市区町村": city,
        "番地": banchi,
        "建物名": building,
        "URL": official_url,
        "SSL": check_ssl(official_url) if official_url else False
    }

def crawl_requests(start_url, max_records=50):
    results = []
    visited_store_urls = set()
    next_page_url = start_url
    session = requests.Session()
    session.headers.update(HEADERS)

    while next_page_url and len(results) < max_records:
        idle()
        try:
            resp = session.get(next_page_url, timeout=15)
        except RequestException as e:
            print("ページ取得失敗:", next_page_url, e)
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        store_links = extract_store_links_from_search(soup)
        # store_links の順に巡回
        for store_link in store_links:
            if len(results) >= max_records:
                break
            if store_link in visited_store_urls:
                continue
            visited_store_urls.add(store_link)
            idle()
            try:
                sresp = session.get(store_link, timeout=15)
            except RequestException as e:
                print("店舗ページ取得失敗:", store_link, e)
                continue
            parsed = parse_store_page(sresp.text, store_link)
            # URLはrequests版では空でもOK（課題ノート）。デフォルトでは空欄にしている。
            if FORCE_EMPTY_URL_FOR_REQUESTS:
                parsed["URL"] = ""
                parsed["SSL"] = False
            results.append(parsed)
            print(f"取得: {parsed['店舗名'][:40]} / {len(results)}/{max_records}")
        # 次ページ探し（"次へ" や ">" ボタン）
        next_link = None
        # ぐるなびの next は a.rel=next のことがある
        a_rel_next = soup.find("a", rel="next")
        if a_rel_next and a_rel_next.get("href"):
            next_link = urljoin(next_page_url, a_rel_next["href"])
        else:
            # テキストが「次へ」「＞」などのaタグ
            for a in soup.find_all("a", href=True):
                if re.search(r"次へ|次ページ|＞|≫|>", a.get_text()):
                    next_link = urljoin(next_page_url, a['href'])
                    break
        if next_link and next_link != next_page_url:
            next_page_url = next_link
        else:
            # 見つからなければ終了
            next_page_url = None

    return results

def main():
    print("スクレイピング開始（requests版）")
    data = crawl_requests(START_SEARCH_URL, MAX_RECORDS)
    df = pd.DataFrame(data, columns=["店舗名","電話番号","メールアドレス","都道府県","市区町村","番地","建物名","URL","SSL"])
    # CSV 出力（Excel での文字化け対策に utf-8-sig）
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"完了: {len(df)} 件を {OUTPUT_CSV} に保存しました。")

if __name__ == "__main__":
    main()
