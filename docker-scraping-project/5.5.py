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
    
    try:
        if url.startswith('https://'):
            hostname = url.split('//')[1].split('/')[0].split(':')[0]
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return True
        return False
    except Exception as e:
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
    building_pattern = r'([ぁ-んァ-ヶー一-龠a-zA-Z]+(?:ビル|タワー|ハイツ|マンション|アパート|ビルディング|プラザ|センター|BLDG|Bldg)[^0-9]*[0-9]*[階F号]?.*?)$'
    building_match = re.search(building_pattern, remaining)
    
    if building_match:
        building = building_match.group(1)
        street = remaining[:building_match.start()]
    else:
        street = remaining
    
    return prefecture, city, street, building

def setup_driver():
    """Seleniumドライバーのセットアップ"""
    options = webdriver.ChromeOptions()
    
    # ユーザーエージェントの設定
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 自動化検出を回避
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # その他のオプション
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    
    # ヘッドレスモード（必要に応じてコメント解除）
    # options.add_argument('--headless')
    
    # ChromeDriverのパスを指定（同じディレクトリにある場合）
    # Windowsの場合: './chromedriver.exe'
    # Mac/Linuxの場合: './chromedriver'
    try:
        service = Service('./chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
    except:
        # パスが不要な場合（PATHに設定されている場合）
        driver = webdriver.Chrome(options=options)
    
    # webdriverプロパティを削除（自動化検出回避）
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
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        page_text = driver.page_source
        emails = re.findall(email_pattern, page_text)
        return emails[0] if emails else ''
    except:
        return ''

def get_official_url(driver):
    """オフィシャルページのURLを取得"""
    try:
        # 複数のパターンでリンクを探す
        link_keywords = [
            "//a[contains(text(), 'ホームページ')]",
            "//a[contains(text(), 'オフィシャル')]",
            "//a[contains(text(), 'HP')]",
            "//a[contains(text(), 'ウェブサイト')]",
            "//a[contains(@class, 'official')]",
            "//a[contains(@href, 'url.asp')]"
        ]
        
        for xpath in link_keywords:
            try:
                link_elem = driver.find_element(By.XPATH, xpath)
                
                # 現在のウィンドウハンドルを保存
                original_window = driver.current_window_handle
                original_url = driver.current_url
                
                # JavaScriptでクリック（より確実）
                driver.execute_script("arguments[0].click();", link_elem)
                time.sleep(3)
                
                # 新しいウィンドウが開いたかチェック
                if len(driver.window_handles) > 1:
                    # 新しいウィンドウに切り替え
                    for window in driver.window_handles:
                        if window != original_window:
                            driver.switch_to.window(window)
                            official_url = driver.current_url
                            driver.close()
                            driver.switch_to.window(original_window)
                            return official_url
                else:
                    # 同じウィンドウで遷移した場合
                    if driver.current_url != original_url:
                        official_url = driver.current_url
                        driver.back()
                        time.sleep(2)
                        return official_url
            except:
                continue
        
        return ''
    except Exception as e:
        return ''

def scrape_restaurant_detail(driver, restaurant_url):
    """個別店舗ページから詳細情報を取得"""
    time.sleep(3)  # アイドリングタイム
    
    try:
        driver.get(restaurant_url)
        wait = WebDriverWait(driver, 10)
        
        # ページの読み込みを待機
        time.sleep(2)
        
        # 店舗名
        name = ''
        name_selectors = [
            (By.CSS_SELECTOR, 'h1.str_name'),
            (By.TAG_NAME, 'h1'),
            (By.XPATH, "//h1[contains(@class, 'shop')]")
        ]
        for by, selector in name_selectors:
            try:
                name_elem = wait.until(EC.presence_of_element_located((by, selector)))
                name = name_elem.text.strip()
                if name:
                    break
            except:
                continue
        
        # 電話番号
        tel = ''
        tel_selectors = [
            (By.CSS_SELECTOR, 'span.tel_num'),
            (By.XPATH, "//span[contains(@class, 'tel')]"),
            (By.XPATH, "//a[starts-with(@href, 'tel:')]")
        ]
        for by, selector in tel_selectors:
            try:
                tel_elem = driver.find_element(by, selector)
                tel = tel_elem.text.strip()
                tel = re.sub(r'[^0-9\-]', '', tel)
                if tel:
                    break
            except:
                continue
        
        # メールアドレス
        email = extract_email(driver)
        
        # 住所
        full_address = ''
        address_selectors = [
            (By.CSS_SELECTOR, 'span[itemprop="address"]'),
            (By.XPATH, "//span[@itemprop='address']"),
            (By.XPATH, "//*[contains(@class, 'address')]")
        ]
        for by, selector in address_selectors:
            try:
                address_elem = driver.find_element(by, selector)
                full_address = address_elem.text.strip()
                if full_address:
                    break
            except:
                continue
        
        prefecture, city, street, building = split_address(full_address)
        
        # URL（オフィシャルページ）
        official_url = get_official_url(driver)
        
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
        print(f"Error scraping {restaurant_url}: {e}")
        return None

def scrape_restaurant_list(search_url, max_records=50):
    """レストラン一覧ページから店舗URLを取得してスクレイピング"""
    driver = setup_driver()
    restaurants_data = []
    
    try:
        driver.get(search_url)
        time.sleep(3)
        
        wait = WebDriverWait(driver, 10)
        
        while len(restaurants_data) < max_records:
            print(f"\n--- Current page, collected: {len(restaurants_data)}/{max_records} ---")
            
            # ページの読み込みを待機
            time.sleep(2)
            
            # 店舗リンクの取得
            restaurant_elements = []
            link_selectors = [
                'a.style_titleLink__oiHVJ',
                'a[href*="/restaurant/"]',
                '.restaurant-item a',
                'a[class*="shop"]'
            ]
            
            for selector in link_selectors:
                try:
                    restaurant_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if restaurant_elements:
                        break
                except:
                    continue
            
            if not restaurant_elements:
                print("No restaurant links found.")
                break
            
            # 現在のページの全店舗URLを事前に取得（StaleElementReferenceError対策）
            restaurant_urls = []
            for elem in restaurant_elements[:max_records - len(restaurants_data)]:
                try:
                    url = elem.get_attribute('href')
                    if url and 'gnavi.co.jp' in url:
                        restaurant_urls.append(url)
                except StaleElementReferenceException:
                    continue
            
            print(f"Found {len(restaurant_urls)} restaurant URLs on this page")
            
            # 各店舗をスクレイピング
            for idx, restaurant_url in enumerate(restaurant_urls):
                if len(restaurants_data) >= max_records:
                    break
                
                print(f"\n[{len(restaurants_data)+1}/{max_records}] Scraping: {restaurant_url}")
                
                restaurant_data = scrape_restaurant_detail(driver, restaurant_url)
                
                if restaurant_data and restaurant_data['店舗名']:
                    restaurants_data.append(restaurant_data)
                    print(f"✓ Success: {restaurant_data['店舗名']}")
                else:
                    print(f"✗ Failed or empty data")
                
                # 一覧ページに戻る
                driver.get(search_url if '?p=' not in search_url else search_url.split('?')[0])
                time.sleep(2)
            
            # すでに十分なデータを取得した場合は終了
            if len(restaurants_data) >= max_records:
                break
            
            # 次のページへ（>ボタンをクリック）
            try:
                time.sleep(3)
                
                # 複数のパターンで次ページボタンを探す
                next_button = None
                next_selectors = [
                    "//a[text()='>']",
                    "//a[contains(@class, 'next')]",
                    "//a[contains(text(), '次へ')]",
                    "//button[contains(@class, 'next')]"
                ]
                
                for selector in next_selectors:
                    try:
                        next_button = driver.find_element(By.XPATH, selector)
                        break
                    except:
                        continue
                
                if next_button:
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(3)
                else:
                    print("No next page button found")
                    break
                    
            except Exception as e:
                print(f"Cannot find next page button: {e}")
                break
    
    finally:
        driver.quit()
    
    return restaurants_data

def main():
    """メイン処理"""
    print("=" * 60)
    print("Web Scraping Tool for Gurunavi (課題1-2: Selenium版)")
    print("=" * 60)
    
    # 検索URL（例：東京都の居酒屋）
    # 実際に使用する検索URLに置き換えてください
    search_url = "https://r.gnavi.co.jp/area/jp/rs/"
    
    print(f"\nTarget URL: {search_url}")
    print(f"Target records: 50")
    print("\nStarting scraping process...")
    print("ChromeDriver will be launched...")
    
    # スクレイピング実行
    restaurants_data = scrape_restaurant_list(search_url, max_records=50)
    
    # 結果の表示
    print("\n" + "=" * 60)
    print(f"Scraping completed!")
    print(f"Total records collected: {len(restaurants_data)}")
    print("=" * 60)
    
    if restaurants_data:
        # DataFrameに変換
        df = pd.DataFrame(restaurants_data)
        
        # カラムの順序を指定
        columns_order = ['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL']
        df = df[columns_order]
        
        # CSV出力（Excel対応のためBOM付きUTF-8）
        output_file = '1-2.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ Data saved to: {output_file}")
        print("\nSample data (first 3 records):")
        print(df.head(3).to_string())
    else:
        print("\n✗ No data collected. Please check the URL and selectors.")

if __name__ == '__main__':
    main()