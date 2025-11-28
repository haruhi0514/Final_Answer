import pandas as pd

df = pd.read_csv('1-2.csv', encoding='utf-8-sig')

print(f"修正前: SSL=True の数: {df['SSL'].sum()}")

df['SSL'] = df['URL'].apply(lambda x: str(x).startswith('https://') if pd.notna(x) else False)

df.to_csv('1-2.csv', index=False, encoding='utf-8-sig')

print(f"修正後: SSL=True の数: {df['SSL'].sum()}")
print("完了！")
