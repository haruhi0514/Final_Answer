import pandas as pd

df = pd.read_csv('1-2.csv', encoding='utf-8-sig')

print("URL列のサンプル:")
print(df['URL'].head(10))

print("\nSSL列のサンプル:")
print(df['SSL'].head(10))

print("\nURL列の値の型:")
for i, url in enumerate(df['URL'].head(5)):
    print(f"{i}: '{url}' (type: {type(url)}) starts with https: {str(url).startswith('https://')}")
