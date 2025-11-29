from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
import pandas as pd
import re
import time
import ssl
import socket

def check_ssl(url):
    """URLのSSL証明書の有無をチェック"""
    if not url or url == '':
        return False
    
    # https→true
    if url.startswith('https://'):
        return True
    else:
        return False

def split_address(full_address):
    """住所を都道府県、市区町村、番地、建物名に分割"""
    prefecture = ''
    city = ''
    street = ''
    building = ''
    
    if not full_address:
        return prefecture, city, street, building
    
    # space delete
    full_address = re.sub(r'\s+', '', full_address)
    
    # todouhukenn
    pref_pattern = r'^(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
    pref_match = re.match(pref_pattern, full_address)
    
    if pref_match:
        prefecture = pref_match.group(1)
        remaining = full_address[len(prefecture):]
    else:
        remaining = full_address
    
    # sikuchousonn
    city_pattern = r'^(.+?[市区町村]|.+?郡.+?[町村])'
    city_match = re.match(city_pattern, remaining)
    
    if city_match:
        city = city_match.group(1)
        remaining = remaining[len(city):]
    
    # tetemono
    building = ''
    if remaining:
        building_patterns = [
            r'([ぁ-んァ-ヶー一-龠a-zA-Z0-9\s]+(?:ビル|タワー|ハイツ|マンション|アパート|ビルディング|プラザ|センター|BLDG|Bldg|GATE|ビレッジ|コート|レジデンス|パーク|スクエア|テラス|荘|館|ハウス).*?)$',
            r'([ぁ-んァ-ヶー一-龠a-zA-Z0-9\s]{2,}[0-9]+[階F号室]+.*?)$',
            r'([0-9]+[階F号室]+.*?)$'
        ]
        
        for pattern in building_patterns:
            building_match = re.search(pattern, remaining)
            if building_match:
                building = building_match.group(1).strip()
                street = remaining[:building_match.start()].strip()
                break
        
        if not building:
            street = remaining.strip()
    
    if building:
        building = re.sub(r'\s+', '', building)
    
    return prefecture, city, street, building

def setup_driver():
    """Seleniumドライバーのセットアップ"""
    options = webdriver.ChromeOptions()
    
    
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    
    
    
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
    except:
        driver = webdriver.Chrome(options=options)
    
    # webdriver
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver

def extract_email(driver):
    """ページからメールアドレスを抽出"""
    try:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        page_text = driver.page_source
        email_matches = re.findall(email_pattern, page_text)
        
        for match in email_matches:
            if not any(x in match.lower() for x in ['.jpg', '.png', '.gif', 'example.com', 'test.com', 'dummy']):
                return match
        return ''
    except:
        return ''

def get_official_url(driver):
    """オフィシャルページのURLを取得"""
    try:
        link_keywords = [
            "//a[contains(text(), 'ホームページ')]",
            "//a[contains(text(), 'オフィシャル')]",
            "//a[contains(text(), '公式')]",
            "//a[contains(text(), 'HP')]",
            "//a[contains(text(), 'WEB')]",
            "//a[contains(text(), 'ウェブサイト')]",
            "//a[contains(@href, 'url.asp')]"
        ]
        
        for xpath in link_keywords:
            try:
                link_elem = driver.find_element(By.XPATH, xpath)
                
                original_window = driver.current_window_handle
                original_url = driver.current_url
                
                # JavaScript
                driver.execute_script("arguments[0].click();", link_elem)
                time.sleep(3)
                
                # check
                if len(driver.window_handles) > 1:
                    for window in driver.window_handles:
                        if window != original_window:
                            driver.switch_to.window(window)
                            official_url = driver.current_url
                            
                            # except url
                            if 'gnavi.co.jp' not in official_url:
                                driver.close()
                                driver.switch_to.window(original_window)
                                return official_url
                            
                            driver.close()
                            driver.switch_to.window(original_window)
                else:
                    # 
                    if driver.current_url != original_url and 'gnavi.co.jp' not in driver.current_url:
                        official_url = driver.current_url
                        driver.back()
                        time.sleep(2)
                        return official_url
                    elif driver.current_url != original_url:
                        driver.back()
                        time.sleep(2)
            except:
                continue
        
        return ''
    except Exception:
        return ''

def scrape_restaurant_detail(driver, restaurant_url):
    """個別店舗ページから詳細情報を取得"""
    time.sleep(3)  
    
    print(f"  アクセス中...")
    
    try:
        driver.get(restaurant_url)
        time.sleep(2)
        
        page_text = driver.page_source
        
        # tennpo
        name = ''
        h1_tags = driver.find_elements(By.TAG_NAME, 'h1')
        if h1_tags:
            name = h1_tags[0].text.strip()
            print(f"  店舗名: {name}")
        
        # tell
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
        address_matches = re.findall(address_pattern, driver.page_source)
        
        if address_matches:
            full_address = max(address_matches, key=len)
            full_address = re.sub(r'\s+', '', full_address)
            print(f"  住所: {full_address}")
        
        prefecture, city, street, building = split_address(full_address)
        print(f"  → 都道府県: {prefecture}")
        print(f"  → 市区町村: {city}")
        print(f"  → 番地: {street}")
        print(f"  → 建物名: {building}")
        
        # mail
        email = ''
        
        # mailto
        try:
            mailto_links = driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
            if mailto_links:
                email = mailto_links[0].get_attribute('href').replace('mailto:', '').strip()
                print(f"  メール: {email}")
        except:
            pass
        
        # text
        if not email:
            email = extract_email(driver)
            if email:
                print(f"  メール: {email}")
        
        # URL
        official_url = get_official_url(driver)
        if official_url:
            print(f"  公式URL: {official_url}")
        
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

def scrape_restaurant_list(search_urls, max_records=50):
    """複数の検索URLから店舗URLを取得してスクレイピング"""
    driver = setup_driver()
    restaurants_data = []
    visited_urls = set()
    
    try:
        for search_url in search_urls:
            if len(restaurants_data) >= max_records:
                break
                
            print(f"\n{'='*60}")
            print(f"検索URL: {search_url}")
            print(f"現在の取得数: {len(restaurants_data)}/{max_records}")
            print('='*60)
            
            driver.get(search_url)
            
            print("ページ読み込み中... 10秒待機")
            time.sleep(10)
            
            # sukuro-ru
            print("スクロール中...")
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # tennpolink
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            restaurant_urls = []
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    
                    if href and href.startswith('https://r.gnavi.co.jp/') and href.count('/') <= 4:
                        
                        if href not in ['https://r.gnavi.co.jp/', 'https://r.gnavi.co.jp/tokyo/']:
                            if href not in visited_urls:
                                
                                clean_url = href.split('?')[0]
                                if clean_url.endswith('/'):
                                    restaurant_urls.append(clean_url)
                                    visited_urls.add(clean_url)
                except StaleElementReferenceException:
                    continue
            
            print(f"発見: {len(restaurant_urls)} 件の新規リンク")
            
            if not restaurant_urls:
                print("新規リンクなし")
                continue
            
            # scr
            for restaurant_url in restaurant_urls:
                if len(restaurants_data) >= max_records:
                    break
                
                print(f"\n[{len(restaurants_data)+1}/{max_records}] {restaurant_url}")
                
                restaurant_data = scrape_restaurant_detail(driver, restaurant_url)
                
                if restaurant_data and restaurant_data['店舗名']:
                    # check
                    if not restaurant_data['市区町村'] or not restaurant_data['番地']:
                        print(f"  ⊘ スキップ（住所情報不足）")
                        continue
                    
                
                    duplicate = False
                    for existing in restaurants_data:
                        if existing['店舗名'] == restaurant_data['店舗名']:
                            duplicate = True
                            print(f"  ⊘ スキップ（店舗名重複）")
                            break
                    
                    if not duplicate:
                        restaurants_data.append(restaurant_data)
                        print(f"  ✓ 取得成功！")
                else:
                    print(f"  ✗ 取得失敗")
                
                # retun
                driver.get(search_url)
                time.sleep(3)
                
                # sukuro-ru
                for i in range(2):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
    
    finally:
        driver.quit()
    
    return restaurants_data

def main():
    """メイン処理"""
    print("=" * 60)
    print("ぐるなび Webスクレイピングツール (課題1-2 Selenium版)")
    print("=" * 60)
    
    # 50 collect
    search_urls = [
        "https://r.gnavi.co.jp/area/tokyo/kods00186/rs/",  
        "https://r.gnavi.co.jp/area/tokyo/rs/?fw=%E5%80%8B%E5%AE%A4",  
        "https://r.gnavi.co.jp/area/tokyo/rs/?fw=%E9%A3%9F%E3%81%B9%E6%94%BE%E9%A1%8C",  
        "https://r.gnavi.co.jp/area/tokyo/rs/?fw=%E5%B1%85%E9%85%92%E5%B1%8B",  
        "https://r.gnavi.co.jp/area/tokyo/rs/?fw=%E7%84%BC%E8%82%89",  
        "https://r.gnavi.co.jp/area/osaka/rs/?fw=%E5%80%8B%E5%AE%A4",  
        "https://r.gnavi.co.jp/area/kanagawa/rs/?fw=%E3%83%A9%E3%83%BC%E3%83%A1%E3%83%B3",  
        "https://r.gnavi.co.jp/area/aichi/rs/?fw=%E5%92%8C%E9%A3%9F",  
        "https://r.gnavi.co.jp/area/fukuoka/rs/?fw=%E3%82%82%E3%81%A4%E9%8D%8B",  
        "https://r.gnavi.co.jp/area/hokkaido/rs/?fw=%E6%B5%B7%E9%AE%AE",  
    ]
    
    print(f"\n検索条件: {len(search_urls)} 件")
    print(f"目標: 50件")
    print("\n開始...\n")
    
    restaurants_data = scrape_restaurant_list(search_urls, max_records=50)
    
    print("\n" + "=" * 60)
    print(f"完了！取得: {len(restaurants_data)} 件")
    print("=" * 60)
    
    if restaurants_data:
        df = pd.DataFrame(restaurants_data)
        
        columns_order = ['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL']
        df = df[columns_order]
        
        output_file = '1-2.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ 保存: {output_file}")
        print("\nサンプル:")
        print(df.head(3).to_string())
        
        print(f"\n統計:")
        print(f"  店舗名あり: {df['店舗名'].notna().sum()} 件")
        print(f"  電話番号あり: {df['電話番号'].notna().sum()} 件")
        print(f"  URLあり: {(df['URL'] != '').sum()} 件")
        print(f"  メールあり: {(df['メールアドレス'] != '').sum()} 件")
    else:
        print("\n✗ データなし")

if __name__ == '__main__':
    main()
