import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import ssl
import socket
from urllib.parse import urljoin, quote

# ユーザーエージェントの設定
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
    
    try:
        response = session.get(restaurant_url, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 店舗名
        name = ''
        name_selectors = [
            'h1.style_restaurantName__9ittY',
            'h1[class*="restaurantName"]',
            'h1.str_name',
            'h1'
        ]
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True)
                break
        
        # 電話番号
        tel = ''
        tel_selectors = [
            'span.style_telefone__oaSwI',
            'span[class*="telefone"]',
            'span.tel_num',
            'a[href^="tel:"]'
        ]
        for selector in tel_selectors:
            tel_elem = soup.select_one(selector)
            if tel_elem:
                tel_text = tel_elem.get_text(strip=True)
                tel = re.sub(r'[^0-9\-]', '', tel_text)
                if tel:
                    break
        
        # メールアドレス
        email = extract_email(soup)
        
        # 住所
        full_address = ''
        address_selectors = [
            'p.style_address__y2WEB',
            'p[class*="address"]',
            'span[itemprop="address"]',
            '.shop-address'
        ]
        for selector in address_selectors:
            address_elem = soup.select_one(selector)
            if address_elem:
                full_address = address_elem.get_text(strip=True)
                break
        
        prefecture, city, street, building = split_address(full_address)
        
        # URL（オフィシャルページ）- 課題1-1では空でOK
        official_url = ''
        
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
        print(f"✗ Error scraping {restaurant_url}: {e}")
        return None

def scrape_restaurant_list(base_search_url, max_records=50):
    """レストラン一覧ページから店舗URLを取得してスクレイピング"""
    session = requests.Session()
    restaurants_data = []
    
    page = 1
    max_pages = 10  # 最大ページ数制限
    
    while len(restaurants_data) < max_records and page <= max_pages:
        print(f"\n{'='*60}")
        print(f"Page {page} をスクレイピング中... (取得済み: {len(restaurants_data)}/{max_records})")
        print('='*60)
        
        time.sleep(3)  # アイドリングタイム
        
        # ページURLの構築
        if page == 1:
            list_url = base_search_url
        else:
            # ページ番号をURLに追加
            if '?' in base_search_url:
                list_url = f"{base_search_url}&p={page}"
            else:
                list_url = f"{base_search_url}?p={page}"
        
        print(f"アクセス中: {list_url}")
        
        try:
            response = session.get(list_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 店舗リンクの取得
            restaurant_links = []
            
            # 複数のセレクタパターンを試行
            link_selectors = [
                'a.style_titleLink__oiHVJ',
                'a[class*="titleLink"]',
                'a[href*="/restaurant/"]'
            ]
            
            for selector in link_selectors:
                elements = soup.select(selector)
                if elements:
                    restaurant_links = elements
                    print(f"✓ セレクタ '{selector}' で {len(elements)} 件発見")
                    break
            
            # 代替方法：全リンクから店舗ページを抽出
            if not restaurant_links:
                all_links = soup.find_all('a', href=True)
                restaurant_links = [
                    link for link in all_links 
                    if '/restaurant/' in link.get('href', '')
                ]
                if restaurant_links:
                    print(f"✓ 代替方法で {len(restaurant_links)} 件発見")
            
            if not restaurant_links:
                print("✗ このページに店舗リンクが見つかりません")
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
                
                print(f"\n[{len(restaurants_data)+1}/{max_records}] {restaurant_url}")
                
                restaurant_data = scrape_restaurant_detail(restaurant_url, session)
                
                if restaurant_data and restaurant_data['店舗名']:
                    restaurants_data.append(restaurant_data)
                    print(f"✓ 成功: {restaurant_data['店舗名']}")
                else:
                    print(f"✗ データ取得失敗")
            
            page += 1
            
        except Exception as e:
            print(f"✗ ページ取得エラー: {e}")
            break
    
    return restaurants_data

def main():
    """メイン処理"""
    print("=" * 60)
    print("ぐるなび Webスクレイピングツール (課題1-1)")
    print("=" * 60)
    
    # 検索URL - 全国の食べ放題レストラン
    search_url = "https://r.gnavi.co.jp/area/jp/rs/?fw=%E9%A3%9F%E3%81%B9%E6%94%BE%E9%A1%8C"
    
    print(f"\n検索URL: {search_url}")
    print(f"目標レコード数: 50")
    print("\nスクレイピング開始...")
    
    # スクレイピング実行
    restaurants_data = scrape_restaurant_list(search_url, max_records=50)
    
    # 結果
    print("\n" + "=" * 60)
    print(f"スクレイピング完了！")
    print(f"取得レコード数: {len(restaurants_data)}")
    print("=" * 60)
    
    if restaurants_data:
        # DataFrameに変換
        df = pd.DataFrame(restaurants_data)
        
        # カラムの順序を指定
        columns_order = ['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL']
        df = df[columns_order]
        
        # CSV出力（Excel対応のためBOM付きUTF-8）
        output_file = '1-1.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ ファイル保存: {output_file}")
        print("\nサンプルデータ (最初の3件):")
        print(df.head(3).to_string())
        
        print(f"\n都道府県別の内訳:")
        print(df['都道府県'].value_counts())
    else:
        print("\n✗ データが取得できませんでした")

if __name__ == '__main__':
    main()