import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import ssl
import socket
from urllib.parse import urljoin


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}

def check_ssl(url):
    if not url or url == '':
        return False
    
    try:
        if url.startswith('https://'):
            hostname = url.split('//')[1].split('/')[0].split(':')[0]
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return True
        return False
    except Exception as e:
        print(f"  SSL確認エラー: {e}")
        return False

def split_address(full_address):
    prefecture = ''
    city = ''
    street = ''
    building = ''
    
    if not full_address:
        return prefecture, city, street, building
    
    full_address = re.sub(r'\s+', '', full_address)
    
    # todouhukenn
    pref_pattern = r'^(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
    pref_match = re.match(pref_pattern, full_address)
    
    if pref_match:
        prefecture = pref_match.group(1)
        remaining = full_address[len(prefecture):]
    else:
        remaining = full_address
    
    # shikuchousonn
    city_pattern = r'^(.+?[市区町村]|.+?郡.+?[町村])'
    city_match = re.match(city_pattern, remaining)
    
    if city_match:
        city = city_match.group(1)
        remaining = remaining[len(city):]
    
    # tatemono
    building_pattern = r'([ぁ-んァ-ヶー一-龠a-zA-Z]+(?:ビル|タワー|ハイツ|マンション|アパート|ビルディング|プラザ|センター|BLDG|Bldg|GATE)[^0-9]*[0-9]*[階F号]?.*?)$'
    building_match = re.search(building_pattern, remaining)
    
    if building_match:
        building = building_match.group(1)
        street = remaining[:building_match.start()]
    else:
        street = remaining
    
    return prefecture, city, street, building

def extract_email(soup):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    text = soup.get_text()
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else ''

def scrape_restaurant_detail(restaurant_url, session):
    time.sleep(3)
    
    print(f"  アクセス中...")
    
    try:
        response = session.get(restaurant_url, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        page_text = soup.get_text()
        
        # tennpo
        name = ''
        
        # jogaikey
        exclude_keywords = ['特集', '忘年会', '歓迎会', '送別会', '新年会', '宴会', 'キャンペーン', '予約', '年会']
        
        # 1
        h1_tags = soup.find_all('h1')
        if h1_tags:
            temp_name = h1_tags[0].get_text(strip=True)
            
            # check
            if not any(keyword in temp_name for keyword in exclude_keywords):
                name = temp_name
                print(f"  店舗名: {name}")
            else:
                print(f"  店舗名候補（除外）: {temp_name}")
        
        # 2
        if not name:
            h2_tags = soup.find_all('h2')
            for h2 in h2_tags:
                temp_name = h2.get_text(strip=True)
                if not any(keyword in temp_name for keyword in exclude_keywords) and len(temp_name) > 2:
                    name = temp_name
                    print(f"  店舗名 (h2): {name}")
                    break
        
        # 3
        if not name:
            name_selectors = [
                '.shop-name',
                '.restaurant-name',
                '[itemprop="name"]',
                '[class*="shopname"]',
                '[class*="storename"]'
            ]
            for selector in name_selectors:
                elem = soup.select_one(selector)
                if elem:
                    temp_name = elem.get_text(strip=True)
                    if not any(keyword in temp_name for keyword in exclude_keywords) and len(temp_name) > 2:
                        name = temp_name
                        print(f"  店舗名 (セレクタ: {selector}): {name}")
                        break
        
        # denwabanngou
        tel = ''
        tel_pattern = r'(\d{2,4}[-\s]?\d{2,4}[-\s]?\d{4})'
        tel_matches = re.findall(tel_pattern, page_text)
        if tel_matches:
            tel = tel_matches[0]
            tel = re.sub(r'\s+', '', tel)
            print(f"  電話番号: {tel}")
        
        # juusho
        full_address = ''
        address_pattern = r'((?:北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県).+?[0-9０-９]+(?:[-−ー][0-9０-９]+)*)'
        address_matches = re.findall(address_pattern, page_text)
        
        if address_matches:
            full_address = max(address_matches, key=len)
            full_address = re.sub(r'\s+', '', full_address)
            print(f"  住所: {full_address}")
        
        prefecture, city, street, building = split_address(full_address)
        print(f"  → 都道府県: {prefecture}")
        print(f"  → 市区町村: {city}")
        print(f"  → 番地: {street}")
        print(f"  → 建物名: {building}")
        
        # mailadress
        email = ''
        
        # 1: mailto
        mailto_links = soup.find_all('a', href=re.compile(r'mailto:'))
        if mailto_links:
            email = mailto_links[0].get('href').replace('mailto:', '').strip()
            print(f"  メール: {email}")
        
        # 2 seikihyougenn
        if not email:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_matches = re.findall(email_pattern, page_text)
            
            for match in email_matches:
                if not any(x in match.lower() for x in ['.jpg', '.png', '.gif', 'example.com', 'test.com', 'dummy']):
                    email = match
                    print(f"  メール: {email}")
                    break
        
        # 3 otoiwase
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
        
        # url
        official_url = ''
        
        url_keywords = ['ホームページ', '公式', 'オフィシャル', 'HP', 'WEB', 'ウェブサイト', 'Website']
        
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            link_href = link.get('href', '')
            
            if any(keyword in link_text for keyword in url_keywords):
                if link_href.startswith('http') and 'gnavi.co.jp' not in link_href:
                    official_url = link_href
                    print(f"  公式URL: {official_url}")
                    break
                
                elif 'url.asp' in link_href or 'link' in link_href:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(link_href)
                    params = urllib.parse.parse_qs(parsed.query)
                    if 'url' in params:
                        official_url = params['url'][0]
                        print(f"  公式URL: {official_url}")
                        break
        
        # ssl
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
    session = requests.Session()
    restaurants_data = []
    visited_urls = set()  # choufuku
    
    page = 1
    max_pages = 10
    
    while len(restaurants_data) < max_records and page <= max_pages:
        print(f"\n{'='*60}")
        print(f"ページ {page} (取得済み: {len(restaurants_data)}/{max_records})")
        print('='*60)
        
        time.sleep(3)
        
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
            
            all_links = soup.find_all('a', href=True)
            restaurant_links = []
            
            for link in all_links:
                href = link.get('href', '')
                
                if '/restaurant/' in href or 'r.gnavi.co.jp' in href:
                    restaurant_links.append(link)
            
            print(f"発見: {len(restaurant_links)} 件のリンク")
            
            if not restaurant_links:
                print("リンクが見つかりません")
                break
            
            # scr
            for idx, link in enumerate(restaurant_links):
                if len(restaurants_data) >= max_records:
                    break
                
                restaurant_url = link.get('href')
                
                if restaurant_url and not restaurant_url.startswith('http'):
                    restaurant_url = urljoin('https://r.gnavi.co.jp', restaurant_url)
                
                # check
                if not restaurant_url or 'gnavi.co.jp' not in restaurant_url:
                    continue
                
                # chouhuku
                if restaurant_url in visited_urls:
                    print(f"  ⊘ スキップ（重複）: {restaurant_url}")
                    continue
                
                visited_urls.add(restaurant_url)
                
                print(f"\n[{len(restaurants_data)+1}/{max_records}] {restaurant_url}")
                
                restaurant_data = scrape_restaurant_detail(restaurant_url, session)
                
                if restaurant_data and restaurant_data['店舗名']:
                    # check
                    if not restaurant_data['市区町村'] or not restaurant_data['番地']:
                        print(f"  ⊘ スキップ（住所情報不足）: 市区町村={restaurant_data['市区町村']}, 番地={restaurant_data['番地']}")
                        continue
                    
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
    print("=" * 60)
    print("ぐるなび Webスクレイピングツール (課題2-2)")
    print("=" * 60)
    
    # urlkwnnsaku
    search_url = "https://r.gnavi.co.jp/area/jp/rs/"
    
    print(f"\n検索URL: {search_url}")
    print(f"目標: 50件")
    print("\n開始...")
    
    # scr
    restaurants_data = scrape_restaurant_list(search_url, max_records=50)
    
    # result
    print("\n" + "=" * 60)
    print(f"完了！取得: {len(restaurants_data)} 件")
    print("=" * 60)
    
    if restaurants_data:
        df = pd.DataFrame(restaurants_data)
        
        # karamu
        columns_order = ['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL']
        df = df[columns_order]
        
        # CSV
        output_file = '2-2.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ 保存: {output_file}")
        print("\nサンプル:")
        print(df.head(3).to_string())
        
        # print
        print(f"\n統計:")
        print(f"  店舗名あり: {df['店舗名'].notna().sum()} 件")
        print(f"  電話番号あり: {df['電話番号'].notna().sum()} 件")
        print(f"  都道府県あり: {df['都道府県'].notna().sum()} 件")
        print(f"  SSL証明書あり: {df['SSL'].sum()} 件")
    else:
        print("\n✗ データなし")

if __name__ == '__main__':
    main()
