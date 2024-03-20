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

    for s,line in enumerate(lines):
        shoken_list = lines[s].split("\n\u3000") 
        for SH in shoken_list:
            if SH.replace("\n","").replace("\u3000","") == "":
                continue
            elif "証券" in SH:
                shoken_company = SH.split("（")[0].replace("\n","")
                rating_base = SH.split("（")[1].replace("）","").replace("\n","")
            else:
                parts = SH.split("――")
                company =  parts[0]. split("（")[0].replace("\n","")
                code = parts[0]. split("（")[1].replace("）","").replace("\n","")
                old_rating = parts[1].split("「")[1].split("」")[0].replace("\n","")
                new_rating = parts[1].split("→")[1].split("、")[0].replace("「","").replace("」","").replace("\n","")
                old_price = parts[1].split("、")[1].split("→")[0].split("円")[0].replace("\n","")
                new_price = parts[1].split("、")[1].split("→")[1].split("円")[0].replace("\n","")
            data.append([shoken_company,rating_base,company, code, old_rating, new_rating, old_price, new_price])

    data_ = pd.DataFrame(data,columns=["証券会社","基準", "銘柄","コード", "従来投資判断", "新投資判断", "従来目標株価", "新目標株価"]).replace("",np.nan).dropna()
    data__ = data_.applymap(to_half_width).astype({"従来目標株価":"int","新目標株価":"int"})
    data__["目標株価引上率"]= 	round((data__["新目標株価"]	- data__["従来目標株価"])/data__["従来目標株価"]*100,1)
    data___ = data__[["銘柄","コード","目標株価引上率","従来目標株価","新目標株価","証券会社","基準","従来投資判断","新投資判断"]]

    st.dataframe(data___)
