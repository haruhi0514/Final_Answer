import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import ssl
import socket
from urllib.parse import urljoin
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}

DB_CONFIG = {
    'host': 'mysql-db',
    'port': 3306,
    'user': 'scraper',
    'password': 'scraper_password',
    'database': 'scraping_db',
    'charset': 'utf8mb4'
}

def create_db_connection():
    connection_string = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
    return create_engine(connection_string, echo=False)

def create_table(engine):
    sql = "CREATE TABLE IF NOT EXISTS ex2_2 (id INT AUTO_INCREMENT PRIMARY KEY, 店舗名 VARCHAR(255), 電話番号 VARCHAR(50), メールアドレス VARCHAR(255), 都道府県 VARCHAR(50), 市区町村 VARCHAR(100), 番地 VARCHAR(255), 建物名 VARCHAR(255), URL VARCHAR(512), SSL BOOLEAN, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("テーブル作成完了")

def check_ssl(url):
    if not url:
        return False
    try:
        if url.startswith('https://'):
            hostname = url.split('//')[1].split('/')[0].split(':')[0]
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return True
    except:
        pass
    return False

def split_address(addr):
    if not addr:
        return '', '', '', ''
    addr = re.sub(r'\s+', '', addr)
    pref_pattern = r'^(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
    pref_match = re.match(pref_pattern, addr)
    pref = pref_match.group(1) if pref_match else ''
    remaining = addr[len(pref):] if pref else addr
    city_pattern = r'^(.+?[市区町村]|.+?郡.+?[町村])'
    city_match = re.match(city_pattern, remaining)
    city = city_match.group(1) if city_match else ''
    remaining = remaining[len(city):] if city else remaining
    building_pattern = r'([ぁ-んァ-ヶー一-龠a-zA-Z]+(?:ビル|タワー|ハイツ|マンション)[^0-9]*[0-9]*[階F号]?.*?)$'
    building_match = re.search(building_pattern, remaining)
    if building_match:
        building = building_match.group(1)
        street = remaining[:building_match.start()]
    else:
        building = ''
        street = remaining
    return pref, city, street, building

def scrape_detail(url, session):
    time.sleep(3)
    try:
        response = session.get(url, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        name = ''
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text(strip=True)
        tel = ''
        tel_matches = re.findall(r'(\d{2,4}[-\s]?\d{2,4}[-\s]?\d{4})', page_text)
        if tel_matches:
            tel = re.sub(r'\s+', '', tel_matches[0])
        addr = ''
        addr_pattern = r'((?:北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県).+?[0-9０-９]+(?:[-−ー][0-9０-９]+)*)'
        addr_matches = re.findall(addr_pattern, page_text)
        if addr_matches:
            addr = max(addr_matches, key=len)
            addr = re.sub(r'\s+', '', addr)
        pref, city, street, building = split_address(addr)
        email = ''
        mailto = soup.find('a', href=re.compile(r'mailto:'))
        if mailto:
            email = mailto.get('href').replace('mailto:', '').strip()
        official_url = ''
        for link in soup.find_all('a', href=True):
            if any(kw in link.get_text(strip=True) for kw in ['ホームページ', '公式', 'HP']):
                href = link.get('href', '')
                if href.startswith('http') and 'gnavi.co.jp' not in href:
                    official_url = href
                    break
        ssl_check = check_ssl(official_url)
        return {'店舗名': name, '電話番号': tel, 'メールアドレス': email, '都道府県': pref, '市区町村': city, '番地': street, '建物名': building, 'URL': official_url, 'SSL': ssl_check}
    except:
        return None

def scrape_list(base_url, max_records=50):
    session = requests.Session()
    data = []
    visited = set()
    page = 1
    while len(data) < max_records and page <= 10:
        print(f"ページ {page} - 取得済み: {len(data)}/{max_records}")
        time.sleep(3)
        list_url = base_url if page == 1 else f"{base_url}?p={page}"
        try:
            response = session.get(list_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [l for l in soup.find_all('a', href=True) if '/restaurant/' in l.get('href', '')]
            for link in links:
                if len(data) >= max_records:
                    break
                url = link.get('href')
                if not url.startswith('http'):
                    url = urljoin('https://r.gnavi.co.jp', url)
                if url in visited:
                    continue
                visited.add(url)
                print(f"[{len(data)+1}] {url[:50]}...")
                result = scrape_detail(url, session)
                if result and result['店舗名'] and result['市区町村'] and result['番地']:
                    data.append(result)
                    print("  OK")
            page += 1
        except Exception as e:
            print(f"エラー: {e}")
            break
    return data

def save_to_mysql(df, engine):
    df.to_sql(name='ex2_2', con=engine, if_exists='append', index=False, method='multi', chunksize=10)
    print(f"MySQL保存完了: {len(df)}件")

def main():
    print("課題2-2 開始")
    engine = create_db_connection()
    print("DB接続OK")
    create_table(engine)
    url = "https://r.gnavi.co.jp/area/jp/rs/"
    data = scrape_list(url, max_records=50)
    print(f"取得完了: {len(data)}件")
    if data:
        df = pd.DataFrame(data)
        df = df[['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL']]
        save_to_mysql(df, engine)
        print("確認SQL:")
        print("SELECT COUNT(URL) FROM ex2_2;")
        print("SHOW COLUMNS FROM ex2_2;")
        print("SELECT * FROM ex2_2 LIMIT 5;")

if __name__ == '__main__':
    main()
ENDOFFILEcat > 2-2.py << 'ENDOFFILE'
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import ssl
import socket
from urllib.parse import urljoin
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}

DB_CONFIG = {
    'host': 'mysql-db',
    'port': 3306,
    'user': 'scraper',
    'password': 'scraper_password',
    'database': 'scraping_db',
    'charset': 'utf8mb4'
}

def create_db_connection():
    connection_string = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
    return create_engine(connection_string, echo=False)

def create_table(engine):
    sql = "CREATE TABLE IF NOT EXISTS ex2_2 (id INT AUTO_INCREMENT PRIMARY KEY, 店舗名 VARCHAR(255), 電話番号 VARCHAR(50), メールアドレス VARCHAR(255), 都道府県 VARCHAR(50), 市区町村 VARCHAR(100), 番地 VARCHAR(255), 建物名 VARCHAR(255), URL VARCHAR(512), SSL BOOLEAN, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("テーブル作成完了")

def check_ssl(url):
    if not url:
        return False
    try:
        if url.startswith('https://'):
            hostname = url.split('//')[1].split('/')[0].split(':')[0]
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return True
    except:
        pass
    return False

def split_address(addr):
    if not addr:
        return '', '', '', ''
    addr = re.sub(r'\s+', '', addr)
    pref_pattern = r'^(北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)'
    pref_match = re.match(pref_pattern, addr)
    pref = pref_match.group(1) if pref_match else ''
    remaining = addr[len(pref):] if pref else addr
    city_pattern = r'^(.+?[市区町村]|.+?郡.+?[町村])'
    city_match = re.match(city_pattern, remaining)
    city = city_match.group(1) if city_match else ''
    remaining = remaining[len(city):] if city else remaining
    building_pattern = r'([ぁ-んァ-ヶー一-龠a-zA-Z]+(?:ビル|タワー|ハイツ|マンション)[^0-9]*[0-9]*[階F号]?.*?)$'
    building_match = re.search(building_pattern, remaining)
    if building_match:
        building = building_match.group(1)
        street = remaining[:building_match.start()]
    else:
        building = ''
        street = remaining
    return pref, city, street, building

def scrape_detail(url, session):
    time.sleep(3)
    try:
        response = session.get(url, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        name = ''
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text(strip=True)
        tel = ''
        tel_matches = re.findall(r'(\d{2,4}[-\s]?\d{2,4}[-\s]?\d{4})', page_text)
        if tel_matches:
            tel = re.sub(r'\s+', '', tel_matches[0])
        addr = ''
        addr_pattern = r'((?:北海道|青森県|岩手県|宮城県|秋田県|山形県|福島県|茨城県|栃木県|群馬県|埼玉県|千葉県|東京都|神奈川県|新潟県|富山県|石川県|福井県|山梨県|長野県|岐阜県|静岡県|愛知県|三重県|滋賀県|京都府|大阪府|兵庫県|奈良県|和歌山県|鳥取県|島根県|岡山県|広島県|山口県|徳島県|香川県|愛媛県|高知県|福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県).+?[0-9０-９]+(?:[-−ー][0-9０-９]+)*)'
        addr_matches = re.findall(addr_pattern, page_text)
        if addr_matches:
            addr = max(addr_matches, key=len)
            addr = re.sub(r'\s+', '', addr)
        pref, city, street, building = split_address(addr)
        email = ''
        mailto = soup.find('a', href=re.compile(r'mailto:'))
        if mailto:
            email = mailto.get('href').replace('mailto:', '').strip()
        official_url = ''
        for link in soup.find_all('a', href=True):
            if any(kw in link.get_text(strip=True) for kw in ['ホームページ', '公式', 'HP']):
                href = link.get('href', '')
                if href.startswith('http') and 'gnavi.co.jp' not in href:
                    official_url = href
                    break
        ssl_check = check_ssl(official_url)
        return {'店舗名': name, '電話番号': tel, 'メールアドレス': email, '都道府県': pref, '市区町村': city, '番地': street, '建物名': building, 'URL': official_url, 'SSL': ssl_check}
    except:
        return None

def scrape_list(base_url, max_records=50):
    session = requests.Session()
    data = []
    visited = set()
    page = 1
    while len(data) < max_records and page <= 10:
        print(f"ページ {page} - 取得済み: {len(data)}/{max_records}")
        time.sleep(3)
        list_url = base_url if page == 1 else f"{base_url}?p={page}"
        try:
            response = session.get(list_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [l for l in soup.find_all('a', href=True) if '/restaurant/' in l.get('href', '')]
            for link in links:
                if len(data) >= max_records:
                    break
                url = link.get('href')
                if not url.startswith('http'):
                    url = urljoin('https://r.gnavi.co.jp', url)
                if url in visited:
                    continue
                visited.add(url)
                print(f"[{len(data)+1}] {url[:50]}...")
                result = scrape_detail(url, session)
                if result and result['店舗名'] and result['市区町村'] and result['番地']:
                    data.append(result)
                    print("  OK")
            page += 1
        except Exception as e:
            print(f"エラー: {e}")
            break
    return data

def save_to_mysql(df, engine):
    df.to_sql(name='ex2_2', con=engine, if_exists='append', index=False, method='multi', chunksize=10)
    print(f"MySQL保存完了: {len(df)}件")

def main():
    print("課題2-2 開始")
    engine = create_db_connection()
    print("DB接続OK")
    create_table(engine)
    url = "https://r.gnavi.co.jp/area/jp/rs/"
    data = scrape_list(url, max_records=50)
    print(f"取得完了: {len(data)}件")
    if data:
        df = pd.DataFrame(data)
        df = df[['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL']]
        save_to_mysql(df, engine)
        print("確認SQL:")
        print("SELECT COUNT(URL) FROM ex2_2;")
        print("SHOW COLUMNS FROM ex2_2;")
        print("SELECT * FROM ex2_2 LIMIT 5;")

if __name__ == '__main__':
    main()
