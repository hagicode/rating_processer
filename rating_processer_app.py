import streamlit as st
import pandas as pd
import numpy as np
import mojimoji

# 半角に変換する関数
def to_half_width(text):
    return mojimoji.zen_to_han(text, kana=False)

# Streamlit app
st.title('Rating Data Processor')

# User input
text = st.text_area("Paste your text here:")

if text:
    text_ = text.replace("◎――トリケミカル、太陽ＨＤ格上げ、ライト工格下げなど","").replace("凡例：銘柄（コード番号）――「従来投資判断」→「新投資判断」、従来目標株価→新目標株価","")
    # データを格納するリスト
    data = []
    # 文章を行ごとに分割
    lines = text_.split("\n\n・")

#市場区分などの情報
url = 'https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls'
df_jpx = pd.read_excel(url)
df_jpx = df_jpx.iloc[:, [1, 2, 3, 5, 7, 9]]
database = df_jpx[df_jpx['市場・商品区分'].isin([ "プライム（内国株式）", "スタンダード（内国株式）","グロース（内国株式）"])].reset_index(drop=True)
database_org = database.astype(str).replace("プライム（内国株式）","東P").replace("スタンダード（内国株式）","東S",).replace("グロース（内国株式）","東G").rename(columns={"市場・商品区分":"市場","33業種区分":"33業種","17業種区分":"17業種","規模区分":"規模"})

shoken_company = ""
rating_base = ""
parts = ""
company =  ""
code = ""
old_rating = ""
new_rating = ""
old_price = ""
new_price = ""

for s,line in enumerate(lines):
    shoken_list = lines[s].split("\n\u3000") 
    for SH in shoken_list:
        if SH.replace("\n","").replace("\u3000","") == "":
            continue
        elif "証券" in SH:
            shoken_company = SH.split("（")[0].replace("\n","")
            rating_base = SH.split("（")[1].split("）")[0].replace("\n","")
            parts = ""
            company =  ""
            code = ""
            old_rating = ""
            new_rating = ""
            old_price = ""
            new_price = ""
        elif SH.count("――") ==1: 
            parts = SH.split("――")
            company =  parts[0]. split("（")[0].replace("\n","")
            code = parts[0]. split("（")[1].replace("）","").replace("\n","")

            if SH.count("「") ==2: 
                old_rating = parts[1].split("「")[1].split("」")[0].replace("\n","")
                new_rating = parts[1].split("→")[1].split("、")[0].replace("「","").replace("」","").replace("\n","")
            
            elif SH.count("「") ==1:
                if parts[1].split("「")[0].count("新規") ==1:
                    old_rating = "新規"
                    new_rating = parts[1].split("「")[1].split("」")[0].replace("\n","")
                elif parts[1].split("「")[0].count("再開") ==1:
                    old_rating = "再開"
                    new_rating = parts[1].split("「")[1].split("」")[0].replace("\n","")
                    
            if SH.count("円") ==2: 
                old_price = parts[1].split("、")[1].split("→")[0].split("円")[0].replace("\n","")
                new_price = parts[1].split("、")[1].split("→")[1].split("円")[0].replace("\n","")
            elif SH.count("円") ==1: 
                old_price = np.nan
                new_price = parts[1].split("、")[1].split("円")[0].replace("\n","")
            elif SH.count("円") ==0: 
                old_price = np.nan
                new_price = np.nan

        data.append([shoken_company,rating_base,company, code, old_rating, new_rating, old_price, new_price])


#data_ = pd.DataFrame(data,columns=["証券会社","基準", "銘柄","コード", "従来投資判断", "新投資判断", "従来目標株価", "新目標株価"]).replace("",np.nan).dropna()
data_ = pd.DataFrame(data,columns=["証券会社","基準", "銘柄","コード", "従来投資判断", "新投資判断", "従来目標株価", "新目標株価"]).replace("",np.nan)
data_ = data_[~data_["コード"].isnull()]
data__ = data_.replace(np.nan,"").applymap(to_half_width).replace("",np.nan).astype({"従来目標株価":"float","新目標株価":"float"})
data__["目標株価引上率"]= 	round((data__["新目標株価"]	- data__["従来目標株価"])/data__["従来目標株価"]*100,1)
data___ = data__[["銘柄","コード","目標株価引上率","従来目標株価","新目標株価","証券会社","基準","従来投資判断","新投資判断"]]

df_merge = pd.merge(data___,database_org,on="コード",how="left")
df_merge_ = df_merge[["コード","銘柄名","市場","33業種","17業種","規模","目標株価引上率","従来目標株価","新目標株価","証券会社","基準","従来投資判断","新投資判断"]]

st.dataframe(df_merge_)
