import pandas as pd

df = pd.read_csv('1-2.csv', encoding='utf-8-sig')

# URLがhttpsで始まっていればTrue
df['SSL'] = df['URL'].apply(lambda x: True if str(x).startswith('https://') else False)

df.to_csv('1-2.csv', index=False, encoding='utf-8-sig')
print("SSL列を修正しました")
