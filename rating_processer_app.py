import streamlit as st
import pandas as pd
import numpy as np
import mojimoji
from urllib.request import urlopen
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import time
import requests
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import datetime
import glob
import pathlib
import os


#github
st.set_page_config(layout="wide")

# Streamlit app
st.title('Rating Data Processor')

#決算スケジュール用
dt_now_jst_aware = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
tgt_month = dt_now_jst_aware.strftime('%Y-%m')
last_month =(dt_now_jst_aware - relativedelta(months=1)).strftime('%Y-%m')

def cook_Kessan_schedule_tgt_month():
  try:
      tgt = "https://nikkeiyosoku.com/stock/financial_statement/month/"+tgt_month
      html = urlopen(tgt)
      bsObj = BeautifulSoup(html, 'html.parser')
      table = bsObj.findAll('table', {'class':"table table-bordered tb-center tb-td3-w10 tb-td4-w10"})[0]
      rows = table.findAll('tr')

      for row in rows:
          rec = []
          for cell in row.findAll(['td', 'th']):
              rec.append(cell.get_text())
          dish1.append(rec)

      rows = table.findAll('tr')
      #print(dish)
      return 'Success'
  except Exception as e:
      return  str(e)

def cook_Kessan_schedule_last_month():
  try:
      tgt = "https://nikkeiyosoku.com/stock/financial_statement/month/"+last_month
      html = urlopen(tgt)
      bsObj = BeautifulSoup(html, 'html.parser')
      table = bsObj.findAll('table', {'class':"table table-bordered tb-center tb-td3-w10 tb-td4-w10"})[0]
      rows = table.findAll('tr')

      for row in rows:
          rec = []
          for cell in row.findAll(['td', 'th']):
              rec.append(cell.get_text())
          dish2.append(rec)

      rows = table.findAll('tr')
      #print(dish)
      return 'Success'
  except Exception as e:
      return  str(e)

@st.cache_data
def get_df_schedule():
    # 元の関数を呼び出す
    cook_Kessan_schedule_tgt_month()
    cook_Kessan_schedule_last_month()

    # データを整形する
    col_names1 = [i.replace("\n","") for i in pd.DataFrame(dish1).loc[0]]
    df_schedule1 = pd.DataFrame(dish1).set_axis(col_names1,axis=1).drop(0)
    code_1 = [i.replace("\n","").replace(" ","")  for i in df_schedule1["銘柄名"]]
    df_schedule1["銘柄名"] = code_1
    code1 = [i.split("(",)[1].replace(")","") for i in df_schedule1["銘柄名"]]
    df_schedule1["コード"] = code1

    col_names2 = [i.replace("\n","") for i in pd.DataFrame(dish2).loc[0]]
    df_schedule2 = pd.DataFrame(dish2).set_axis(col_names2,axis=1).drop(0)
    code_2 = [i.replace("\n","").replace(" ","")  for i in df_schedule2["銘柄名"]]
    df_schedule2["銘柄名"] = code_2
    code2 = [i.split("(",)[1].replace(")","") for i in df_schedule2["銘柄名"]]
    df_schedule2["コード"] = code2

    # データを結合する
    df_schedule = pd.concat([df_schedule2,df_schedule1],axis=0)

    return df_schedule

dish1 = []
dish2 = []
df_schedule = get_df_schedule().rename(columns={"発表日":"決算発表日"})
df_schedule_ = df_schedule[["決算発表日","コード"]]
df_schedule_["決算発表日"] = pd.to_datetime(str(dt_now_jst_aware.year)+"/"+df_schedule_["決算発表日"]).dt.strftime('%m/%d')

# 半角に変換する関数
def to_half_width(text):
    return mojimoji.zen_to_han(text, kana=False)

# dfに色を付ける関数
def color_cells(val):
    color = 'red' if val > 0 else 'blue' if val < 0 else 'black'
    return 'color: %s' % color

def highlight_dates(val):
    today = pd.to_datetime(dt_now_jst_aware.date())
    yesterday = pd.to_datetime(today - timedelta(days=1))
    day_before_yesterday = pd.to_datetime(today - timedelta(days=2))

    if val == today:
        color = 'yellow'  # 今日のデータの色
    elif val == yesterday:
        color = 'orange'  # 昨日のデータの色
    elif val == day_before_yesterday:
        color = 'red'    # 一昨日のデータの色
    else:
        color = 'black'  # それ以外のデータの色

    return f'color: {color}'







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

#テーマ情報
l2 = sorted(glob.glob('*.csv', recursive=True))
p = pathlib.Path(l2[-1])
theme_df = pd.read_csv(p,encoding="cp932")
theme_df_ = theme_df.replace(0,np.nan)


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

df_merge_kessan = pd.merge(df_schedule_,df_merge_ ,on="コード",how="right")

#themeとの結合
df_merge_kessan_theme = pd.merge(df_merge_kessan,theme_df_,on="コード",how="left")
df_merge_kessan_theme_=df_merge_kessan_theme.dropna(how='all', axis=1)

#themeの要約＋順番
theme_summary = df_merge_kessan_theme_.drop(df_merge_kessan.columns,axis=1).describe().T["count"].sort_values(ascending=False)
col_index= df_merge_kessan.columns.tolist()+theme_summary.index.tolist()
df_merge_kessan_theme__=df_merge_kessan_theme_.reindex(columns=col_index)

df_merge_style = df_merge_kessan_theme__.style.applymap(color_cells, subset=["目標株価引上率"])
#df_merge_style_ = df_merge_style.reset_index().style.applymap(highlight_dates, subset=["決算発表日"])

#df_merge_：元の表
#df_stat_scal：規模統計
#df_stat_33：業種統計

df_stat = df_merge_[~df_merge_["目標株価引上率"].isnull()]
plus = (df_stat["目標株価引上率"]>=0).astype(int)
minas = (df_stat["目標株価引上率"]<0).astype(int)
df_stat["プラス"]=plus
df_stat["マイナス"]=minas

df_stat_scal = pd.concat([df_stat.groupby("規模")["目標株価引上率"].mean(),df_stat.groupby("規模")["プラス"].sum(),df_stat.groupby("規模")["マイナス"].sum()],axis=1)
df_stat_scal["割合"]=round((df_stat_scal["プラス"]-df_stat_scal["マイナス"])/(df_stat_scal["プラス"]+df_stat_scal["マイナス"]),2)
df_stat_33 = pd.concat([df_stat.groupby("33業種")["目標株価引上率"].mean(),df_stat.groupby("33業種")["プラス"].sum(),df_stat.groupby("33業種")["マイナス"].sum()],axis=1)
df_stat_33["割合"]=round((df_stat_33["プラス"]-df_stat_33["マイナス"])/(df_stat_33["プラス"]+df_stat_33["マイナス"]),2)





col1, col2 = st.columns(2)

col1.dataframe(df_stat_scal,use_container_width=True)
col2.dataframe(df_stat_33,use_container_width=True)
st.dataframe(theme_summary,use_container_width=True)
st.dataframe(df_merge_style,use_container_width=True)

@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('cp932')
csv = convert_df(df_merge_style)

st.download_button(
    label="Download data as CSV",
    data=csv,
    file_name='レーティング.csv',
    mime='text/csv',
)