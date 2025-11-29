python3 << 'ENDOFPYTHON'
code = '''#!/usr/bin/env python3
# coding: utf-8
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import ssl
import socket
from urllib.parse import urljoin
from sqlalchemy import create_engine, text

HEADERS = {'User-Agent': 'Mozilla/5.0'}
DB_CONFIG = {'host': 'mysql-db', 'port': 3306, 'user': 'scraper', 'password': 'scraper_password', 'database': 'scraping_db', 'charset': 'utf8mb4'}

def create_db_connection():
    cs = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"
    return create_engine(cs, echo=False)

def create_table(engine):
    sql = "CREATE TABLE IF NOT EXISTS ex2_2 (id INT AUTO_INCREMENT PRIMARY KEY, shop_name VARCHAR(255), phone VARCHAR(50), email VARCHAR(255), prefecture VARCHAR(50), city VARCHAR(100), street VARCHAR(255), building VARCHAR(255), url VARCHAR(512), has_ssl BOOLEAN) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("Table created")

def check_ssl(url):
    if not url or not url.startswith('https://'):
        return False
    try:
        hostname = url.split('//')[1].split('/')[0].split(':')[0]
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname):
                return True
    except:
        return False

def split_addr(addr):
    if not addr:
        return '', '', '', ''
    addr = re.sub(r'\\s+', '', addr)
    pm = re.match(r'^(北海道|.+?[都道府県])', addr)
    pref = pm.group(1) if pm else ''
    rem = addr[len(pref):]
    cm = re.match(r'^(.+?[市区町村])', rem)
    city = cm.group(1) if cm else ''
    rem = rem[len(city):]
    return pref, city, rem, ''

def scrape_one(url, sess):
    time.sleep(3)
    try:
        r = sess.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')
        txt = soup.get_text()
        name = soup.find('h1').get_text(strip=True) if soup.find('h1') else ''
        tel_m = re.findall(r'(\\d{2,4}[-\\s]?\\d{2,4}[-\\s]?\\d{4})', txt)
        tel = re.sub(r'\\s+', '', tel_m[0]) if tel_m else ''
        addr_m = re.findall(r'((?:北海道|東京都|京都府|大阪府|.+?県).+?[0-9]+[-]?[0-9]*)', txt)
        addr = max(addr_m, key=len) if addr_m else ''
        pref, city, street, building = split_addr(addr)
        mailto = soup.find('a', href=re.compile(r'mailto:'))
        email = mailto.get('href').replace('mailto:', '').strip() if mailto else ''
        ourl = ''
        for lnk in soup.find_all('a', href=True):
            if any(k in lnk.get_text(strip=True) for k in ['HP', 'ホ', '公']):
                h = lnk.get('href', '')
                if h.startswith('http') and 'gnavi' not in h:
                    ourl = h
                    break
        return {'shop_name': name, 'phone': tel, 'email': email, 'prefecture': pref, 'city': city, 'street': street, 'building': building, 'url': ourl, 'has_ssl': check_ssl(ourl)}
    except:
        return None

def scrape_all(base_url, max_n=50):
    sess = requests.Session()
    data = []
    visited = set()
    page = 1
    while len(data) < max_n and page <= 30:
        print(f"Page {page} - Got {len(data)}/{max_n}")
        time.sleep(3)
        url = base_url if page == 1 else f"{base_url}?p={page}"
        try:
            r = sess.get(url, headers=HEADERS, timeout=15)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            all_links = soup.find_all('a', href=True)
            links = []
            for link in all_links:
                href = link.get('href', '')
                if 'r.gnavi.co.jp/r' in href and '/plan/' not in href and href not in visited:
                    links.append(href)
            links = list(set(links))
            for href in links:
                if len(data) >= max_n:
                    break
                if not href.startswith('http'):
                    href = urljoin('https://r.gnavi.co.jp', href)
                if href in visited:
                    continue
                visited.add(href)
                print(f"  [{len(data)+1}] Fetching...")
                item = scrape_one(href, sess)
                if item and item['shop_name']:
                    if item['city'] and item['street']:
                        data.append(item)
                        print(f"    OK: {item['shop_name'][:30]}")
            page += 1
        except Exception as e:
            print(f"Error: {e}")
            break
    return data

def save_db(df, eng):
    df.to_sql('ex2_2', eng, if_exists='append', index=False, method='multi', chunksize=10)
    print(f"\\nSaved to MySQL: {len(df)} records")

def main():
    print("="*60)
    print("Task 2-2")
    print("="*60)
    eng = create_db_connection()
    print("DB connected")
    create_table(eng)
    data = scrape_all("https://r.gnavi.co.jp/area/tokyo/rs/", 50)
    print(f"\\nCompleted: {len(data)} records")
    if data:
        df = pd.DataFrame(data)
        df = df[['shop_name', 'phone', 'email', 'prefecture', 'city', 'street', 'building', 'url', 'has_ssl']]
        save_db(df, eng)

if __name__ == '__main__':
    main()
'''

with open('2-2.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("File 2-2.py created")
ENDOFPYTHON
