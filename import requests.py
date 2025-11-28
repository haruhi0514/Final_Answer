import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import ssl
import socket
from urllib.parse import urljoin

# ユーザーエージェントの設定
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}

def check_ssl(url):
    """URLのSSL証明書の有無をチェック"""
    if not url or url == '':
        return False
    
    try:
        if url.startswith('https://'):
            hostname = url.split('//')[1].split('/')[0].split(':')[0]
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return True
        return False
    except Exception:
        return False

def split_address(full_address):
    """住所を都道府県、市区町村、番地、建物名に分割"""
    prefecture = ''
    city = ''
    street = ''
    building = ''
    
    if not full_address:
        return prefecture, city, street, building
    
    # 空白文字を削除
    full_address = re.sub(r'\s+', '', full_address)
    
    # 都道府県の抽出
    pref_pattern = r'^(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
    pref_match = re.match(pref_pattern, full_address)
    
    if pref_match:
        prefecture = pref_match.group(1)
        remaining = full_address[len(prefecture):]
    else:
        remaining = full_address
    
    # 市区町村の抽出
    city_pattern = r'^(.+?[市区町村]|.+?郡.+?[町村])'
    city_match = re.match(city_pattern, remaining)
    
    if city_match:
        city = city_match.group(1)
        remaining = remaining[len(city):]
    
    # 建物名の抽出
    building_pattern = r'([ぁ-んァ-ヶー一-龠a-zA-Z]+(?:ビル|タワー|ハイツ|マンション|アパート|ビルディング|プラザ|センター|BLDG|Bldg|GATE)[^0-9]*[0-9]*[階F号]?.*?)$'
    building_match = re.search(building_pattern, remaining)
    
    if building_match:
        building = building_match.group(1)
        street = remaining[:building_match.start()]
    else:
        street = remaining
    
    return prefecture, city, street, building

def extract_email(soup):
    """ページからメールアドレスを抽出"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    text = soup.get_text()
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else ''

def scrape_restaurant_detail(restaurant_url, session):
    """個別店舗ページから詳細情報を取得"""
    time.sleep(3)  # アイドリングタイム
    
    print(f"  アクセス中...")
    
    try:
        response = session.get(restaurant_url, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # デバッグ用：ページのテキスト全体を取得
        page_text = soup.get_text()
        
        # 店舗名の取得（複数のパターンを試行）
        name = ''
        
        # パターン1: h1タグから
        h1_tags = soup.find_all('h1')
        if h1_tags:
            name = h1_tags[0].get_text(strip=True)
            print(f"  店舗名: {name}")
        
        # パターン2: より多くのセレクタを試行
        if not name:
            name_selectors = [
                'h1',
                '[class*="restaurant"]',
                '[class*="shop"]',
                '[class*="store"]',
                'h2'
            ]
            for selector in name_selectors:
                elem = soup.select_one(selector)
                if elem:
                    name = elem.get_text(strip=True)
                    if len(name) > 3:  # 3文字以上なら店舗名として採用
                        print(f"  店舗名 (セレクタ: {selector}): {name}")
                        break
        
        # 電話番号の取得（正規表現でページ全体から探す）
        tel = ''
        tel_pattern = r'(\d{2,4}[-\s]?\d{2,4}[-\s]?\d{4})'
        tel_matches = re.findall(tel_pattern, page_text)
        if tel_matches:
            # 最初に見つかった電話番号を使用
            tel = tel_matches[0]
            tel = re.sub(r'\s+', '', tel)  # 空白を削除
            print(f"  電話番号: {tel}")
        
        # 住所の取得（正規表現で都道府県から始まる部分を探す）
        full_address = ''
        address_pattern = r'((?:北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県).+?[0-9０-９]+(?:[-−ー][0-9０-９]+)*)'
        address_matches = re.findall(address_pattern, page_text)
        
        if address_matches:
            # 最も長い住所を採用（より完全な住所の可能性が高い）
            full_address = max(address_matches, key=len)
            # 改行や余分な空白を削除
            full_address = re.sub(r'\s+', '', full_address)
            print(f"  住所: {full_address}")
        
        # 住所を分割
        prefecture, city, street, building = split_address(full_address)
        print(f"  → 都道府県: {prefecture}")
        print(f"  → 市区町村: {city}")
        print(f"  → 番地: {street}")
        print(f"  → 建物名: {building}")
        
        # メールアドレス（より詳細に検索）
        email = ''
        
        # パターン1: mailtoリンクから
        mailto_links = soup.find_all('a', href=re.compile(r'mailto:'))
        if mailto_links:
            email = mailto_links[0].get('href').replace('mailto:', '').strip()
            print(f"  メール: {email}")
        
        # パターン2: テキストから正規表現で検索
        if not email:
            # より厳密なメールアドレスパターン
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, page_text)
            
            # 一般的でないドメインのメールを優先（info@, contact@など）
            for match in email_matches:
                # 画像ファイルやダミーアドレスを除外
                if not any(x in match.lower() for x in ['.jpg', '.png', '.gif', 'example.com', 'test.com', 'dummy']):
                    email = match
                    print(f"  メール: {email}")
                    break
        
        # パターン3: 「お問い合わせ」セクションから探す
        if not email:
            contact_sections = soup.find_all(['div', 'p', 'span'], text=re.compile(r'[Ee]-?mail|メール|お問い合わせ'))
            for section in contact_sections:
                parent = section.find_parent()
                if parent:
                    parent_text = parent.get_text()
                    email_matches = re.findall(email_pattern, parent_text)
                    if email_matches:
                        email = email_matches[0]
                        print(f"  メール: {email}")
                        break
        
        # URL（オフィシャルページ）
        official_url = ''
        # 「ホームページ」「公式サイト」などのリンクを探す
        url_keywords = ['ホームページ', '公式', 'オフィシャル', 'HP', 'WEB', 'ウェブサイト', 'Website']
        
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            link_href = link.get('href', '')
            
            # キーワードを含むリンクを探す
            if any(keyword in link_text for keyword in url_keywords):
                # ぐるなび以外のURLを取得
                if link_href.startswith('http') and 'gnavi.co.jp' not in link_href:
                    official_url = link_href
                    print(f"  公式URL: {official_url}")
                    break
                # url.aspのようなリダイレクトURLの場合
                elif 'url.asp' in link_href or 'link' in link_href:
                    # リダイレクト先のURLを取得（クエリパラメータから）
                    import urllib.parse
                    parsed = urllib.parse.urlparse(link_href)
                    params = urllib.parse.parse_qs(parsed.query)
                    if 'url' in params:
                        official_url = params['url'][0]
                        print(f"  公式URL: {official_url}")
                        break
        
        # SSL
        has_ssl = check_ssl(official_url)
        
        return {
            '店舗名': name,
            '電話番号': tel,
            'メールアドレス': email,
            '都道府県': prefecture,
            '市区町村': city,
            '番地': street,
            '建物名': building,
            'URL': official_url,
            'SSL': has_ssl
        }
    
    except Exception as e:
        print(f"  ✗ エラー: {e}")
        return None

def scrape_restaurant_list(base_search_url, max_records=50):
    """レストラン一覧ページから店舗URLを取得してスクレイピング"""
    session = requests.Session()
    restaurants_data = []
    visited_urls = set()  # 重複チェック用
    
    page = 1
    max_pages = 10
    
    while len(restaurants_data) < max_records and page <= max_pages:
        print(f"\n{'='*60}")
        print(f"ページ {page} (取得済み: {len(restaurants_data)}/{max_records})")
        print('='*60)
        
        time.sleep(3)  # アイドリングタイム
        
        # ページURLの構築
        if page == 1:
            list_url = base_search_url
        else:
            if '?' in base_search_url:
                list_url = f"{base_search_url}&p={page}"
            else:
                list_url = f"{base_search_url}?p={page}"
        
        print(f"アクセス: {list_url}")
        
        try:
            response = session.get(list_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 全てのリンクから店舗ページを抽出
            all_links = soup.find_all('a', href=True)
            restaurant_links = []
            
            for link in all_links:
                href = link.get('href', '')
                # /restaurant/ を含むリンクを店舗ページとみなす
                if '/restaurant/' in href or 'r.gnavi.co.jp' in href:
                    restaurant_links.append(link)
            
            print(f"発見: {len(restaurant_links)} 件のリンク")
            
            if not restaurant_links:
                print("リンクが見つかりません")
                break
            
            # 各店舗をスクレイピング
            for idx, link in enumerate(restaurant_links):
                if len(restaurants_data) >= max_records:
                    break
                
                restaurant_url = link.get('href')
                
                # 相対URLを絶対URLに変換
                if restaurant_url and not restaurant_url.startswith('http'):
                    restaurant_url = urljoin('https://r.gnavi.co.jp', restaurant_url)
                
                # 有効なURLかチェック
                if not restaurant_url or 'gnavi.co.jp' not in restaurant_url:
                    continue
                
                # 重複チェック
                if restaurant_url in visited_urls:
                    print(f"  ⊘ スキップ（重複）: {restaurant_url}")
                    continue
                
                visited_urls.add(restaurant_url)
                
                print(f"\n[{len(restaurants_data)+1}/{max_records}] {restaurant_url}")
                
                restaurant_data = scrape_restaurant_detail(restaurant_url, session)
                
                if restaurant_data and restaurant_data['店舗名']:
                    # 必須項目のチェック（市区町村と番地が必須）
                    if not restaurant_data['市区町村'] or not restaurant_data['番地']:
                        print(f"  ⊘ スキップ（住所情報不足）: 市区町村={restaurant_data['市区町村']}, 番地={restaurant_data['番地']}")
                        continue
                    
                    # 店舗名での重複チェックも追加
                    duplicate = False
                    for existing in restaurants_data:
                        if existing['店舗名'] == restaurant_data['店舗名']:
                            duplicate = True
                            print(f"  ⊘ スキップ（店舗名重複）: {restaurant_data['店舗名']}")
                            break
                    
                    if not duplicate:
                        restaurants_data.append(restaurant_data)
                        print(f"  ✓ 取得成功！")
                else:
                    print(f"  ✗ 取得失敗")
            
            page += 1
            
        except Exception as e:
            print(f"✗ エラー: {e}")
            break
    
    return restaurants_data

def main():
    """メイン処理"""
    print("=" * 60)
    print("ぐるなび Webスクレイピングツール (課題1-1 改善版)")
    print("=" * 60)
    
    # 検索URL
    search_url = "https://r.gnavi.co.jp/area/jp/rs/"
    
    print(f"\n検索URL: {search_url}")
    print(f"目標: 50件")
    print("\n開始...")
    
    # スクレイピング実行
    restaurants_data = scrape_restaurant_list(search_url, max_records=50)
    
    # 結果
    print("\n" + "=" * 60)
    print(f"完了！取得: {len(restaurants_data)} 件")
    print("=" * 60)
    
    if restaurants_data:
        # DataFrameに変換
        df = pd.DataFrame(restaurants_data)
        
        # カラムの順序
        columns_order = ['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL']
        df = df[columns_order]
        
        # CSV出力
        output_file = '1-1.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ 保存: {output_file}")
        print("\nサンプル:")
        print(df.head(3).to_string())
        
        # 取得できたデータの統計
        print(f"\n統計:")
        print(f"  店舗名あり: {df['店舗名'].notna().sum()} 件")
        print(f"  電話番号あり: {df['電話番号'].notna().sum()} 件")
        print(f"  都道府県あり: {df['都道府県'].notna().sum()} 件")
    else:
        print("\n✗ データなし")

if __name__ == '__main__':
    main()
    