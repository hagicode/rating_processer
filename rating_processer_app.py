import streamlit as st
import pandas as pd
import numpy as np
import mojimoji
from urllib.request import urlopen
from bs4 import BeautifulSoup
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import glob
import pathlib
import os

# --- 設定 ---
st.set_page_config(layout="wide")
st.title('Rating Data Processor')

# タイムゾーン設定
dt_now_jst_aware = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
tgt_month = dt_now_jst_aware.strftime('%Y-%m')
last_month = (dt_now_jst_aware - relativedelta(months=1)).strftime('%Y-%m')

# --- 関数定義 ---

def cook_Kessan_schedule(month_str):
    """指定した月の決算スケジュールを取得する"""
    dish = []
    try:
        tgt = f"https://nikkeiyosoku.com/stock/financial_statement/month/{month_str}"
        html = urlopen(tgt)
        bsObj = BeautifulSoup(html, 'html.parser')
        table = bsObj.findAll('table', {'class':"table table-bordered tb-center tb-td3-w10 tb-td4-w10"})[0]
        rows = table.findAll('tr')

        for row in rows:
            rec = []
            for cell in row.findAll(['td', 'th']):
                rec.append(cell.get_text())
            dish.append(rec)
        return dish
    except Exception as e:
        st.error(f"Scraping Error ({month_str}): {e}")
        return []

@st.cache_data
def get_df_schedule():
    # データを取得
    dish_tgt = cook_Kessan_schedule(tgt_month)
    dish_last = cook_Kessan_schedule(last_month)

    def process_dish(dish):
        if not dish: return pd.DataFrame()
        df = pd.DataFrame(dish)
        col_names = [i.replace("\n","") for i in df.loc[0]]
        df = df.set_axis(col_names, axis=1).drop(0)
        df["銘柄名"] = df["銘柄名"].str.replace("\n","").str.replace(" ","")
        df["コード"] = df["銘柄名"].apply(lambda x: x.split("(")[1].replace(")","") if "(" in x else "")
        return df

    df1 = process_dish(dish_tgt)
    df2 = process_dish(dish_last)
    
    df_schedule = pd.concat([df2, df1], axis=0).drop_duplicates(subset=['コード'])
    return df_schedule

def to_half_width(text):
    if isinstance(text, str):
        return mojimoji.zen_to_han(text, kana=False)
    return text

def color_cells(val):
    if isinstance(val, (int, float)):
        color = 'red' if val > 0 else 'blue' if val < 0 else 'black'
        return f'color: {color}'
    return ''

# --- データ処理開始 ---

# 1. 決算スケジュールの取得
df_schedule = get_df_schedule().rename(columns={"発表日":"決算発表日"})
df_schedule_ = df_schedule[["決算発表日","コード"]].copy()
# 年を補完してフォーマット
df_schedule_["決算発表日"] = df_schedule_["決算発表日"].apply(lambda x: f"{dt_now_jst_aware.year}/{x}")
df_schedule_["決算発表日"] = pd.to_datetime(df_schedule_["決算発表日"], errors='coerce').dt.strftime('%m/%d')

# 2. 市場区分データの取得
@st.cache_data
def get_jpx_data():
    url = 'https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls'
    df = pd.read_excel(url)
    df = df.iloc[:, [1, 2, 3, 5, 7, 9]]
    df.columns = ["コード", "銘柄名", "市場", "33業種", "17業種", "規模"]
    target_markets = ["プライム（内国株式）", "スタンダード（内国株式）", "グロース（内国株式）"]
    df = df[df['市場'].isin(target_markets)].copy()
    df['市場'] = df['市場'].replace({"プライム（内国株式）":"東P", "スタンダード（内国株式）":"東S", "グロース（内国株式）":"東G"})
    return df.astype(str)

database_org = get_jpx_data()

# 3. テーマ情報の読み込み
l2 = sorted(glob.glob('*.csv', recursive=True))
if l2:
    p = pathlib.Path(l2[-1])
    theme_df = pd.read_csv(p, encoding="cp932")
    theme_df_ = theme_df.replace(0, np.nan)
else:
    theme_df_ = pd.DataFrame(columns=["コード"])

# --- UI: テキスト入力 ---
text = st.text_area("Paste your text here (Rating data):", height=200)

if text:
    # クリーニング
    text_clean = text.replace("◎――トリケミカル、太陽ＨＤ格上げ、ライト工格下げなど","")\
                     .replace("凡例：銘柄（コード番号）――「従来投資判断」→「新投資判断」、従来目標株価→新目標株価","")\
                     .replace("（画像クリックで「きょうの目標株価カイ離率ランキング」拡大版にジャンプ）","")
    
    lines = text_clean.split("\n\n・")
    data = []

    current_shoken = ""
    current_base = ""

    for line in lines:
        sub_lines = line.split("\n\u3000")
        for SH in sub_lines:
            content = SH.strip()
            if not content: continue
            
            if "証券" in content and "（" in content:
                current_shoken = content.split("（")[0].replace("\n","")
                current_base = content.split("（")[1].split("）")[0].replace("\n","")
                continue
            
            if "――" in content:
                parts = content.split("――")
                name_code = parts[0]
                company_name = name_code.split("（")[0].strip()
                code_val = name_code.split("（")[1].replace("）","").strip() if "（" in name_code else ""
                
                old_rating, new_rating = np.nan, np.nan
                old_price, new_price = np.nan, np.nan
                
                # レーティング抽出
                if "「" in parts[1]:
                    if parts[1].count("「") == 2:
                        old_rating = parts[1].split("「")[1].split("」")[0]
                        new_rating = parts[1].split("→")[1].split("、")[0].replace("「","").replace("」","")
                    elif "新規" in parts[1]:
                        old_rating = "新規"
                        new_rating = parts[1].split("「")[1].split("」")[0]
                
                # 株価抽出
                if "円" in parts[1]:
                    prices = parts[1].split("、")[-1]
                    if "→" in prices:
                        old_price_str = prices.split("→")[0].replace("円","").replace(",","").strip()
                        new_price_str = prices.split("→")[1].replace("円","").replace(",","").strip()
                        old_price = float(old_price_str) if old_price_str.isdigit() else np.nan
                        new_price = float(new_price_str) if new_price_str.isdigit() else np.nan
                    else:
                        new_price_str = prices.replace("円","").replace(",","").strip()
                        new_price = float(new_price_str) if new_price_str.isdigit() else np.nan

                data.append([current_shoken, current_base, company_name, code_val, old_rating, new_rating, old_price, new_price])

    # DataFrame作成
    df_raw = pd.DataFrame(data, columns=["証券会社","基準", "銘柄","コード", "従来投資判断", "新投資判断", "従来目標株価", "新目標株価"])
    df_raw = df_raw.dropna(subset=["コード"])
    
    # 全角半角変換と型変換
    df_raw["コード"] = df_raw["コード"].apply(to_half_width)
    df_raw["目標株価引上率"] = round((df_raw["新目標株価"] - df_raw["従来目標株価"]) / df_raw["従来目標株価"] * 100, 1)
    
    # 結合処理
    df_merge = pd.merge(df_raw, database_org, on="コード", how="left")
    df_merge_kessan = pd.merge(df_schedule_, df_merge, on="コード", how="right")
    df_final = pd.merge(df_merge_kessan, theme_df_, on="コード", how="left").dropna(how='all', axis=1)

    # テーマ要約
    theme_cols = [c for c in df_final.columns if c not in df_merge_kessan.columns]
    theme_summary = df_final[theme_cols].count().sort_values(ascending=False)

    # 表示
    st.subheader("📊 統計・サマリー")
    df_stat = df_final.dropna(subset=["目標株価引上率"]).copy()
    df_stat["プラス"] = (df_stat["目標株価引上率"] >= 0).astype(int)
    df_stat["マイナス"] = (df_stat["目標株価引上率"] < 0).astype(int)

    c1, c2 = st.columns(2)
    with c1:
        st.write("【規模別】")
        stat_scale = df_stat.groupby("規模").agg({"目標株価引上率":"mean", "プラス":"sum", "マイナス":"sum"})
        st.dataframe(stat_scale, use_container_width=True)
    with c2:
        st.write("【業種別】")
        stat_33 = df_stat.groupby("33業種").agg({"目標株価引上率":"mean", "プラス":"sum", "マイナス":"sum"})
        st.dataframe(stat_33, use_container_width=True)

    st.write("【テーマ出現数】")
    st.dataframe(theme_summary, use_container_width=True)

    st.subheader("📝 レーティング詳細一覧")
    st.dataframe(df_final.style.map(color_cells, subset=["目標株価引上率"]), use_container_width=True)

    # SBIインポート用作成
    st.subheader("📥 SBI証券インポート用")
    df_dw = df_final.copy()
    
    # テーマを1つの文字列に結合
    for col in theme_cols:
        df_dw[col] = df_dw[col].apply(lambda x: col if pd.notnull(x) and x >= 1 else np.nan)
    
    df_dw['themes'] = df_dw[theme_cols].apply(lambda row: ', '.join(row.dropna().astype(str)), axis=1)
    
    df_sbi = pd.DataFrame()
    df_sbi["C1"] = df_dw["コード"]
    df_sbi["C2"] = ""
    df_sbi["C3"] = "TKY"
    df_sbi["C4"] = ""
    df_sbi["C5"] = ""
    df_sbi["C6"] = ""
    df_sbi["C7"] = ""
    df_sbi["C8"] = ""
    df_sbi["C9"] = df_dw.apply(lambda r: f"({r['目標株価引上率']}){r['決算発表日']}[{r['themes']}]", axis=1)

    sort_opt = st.selectbox('ソート順:', ['目標株価引上率', '決算発表日'])
    df_sbi = df_sbi.sort_values(by="C9" if sort_opt=='決算発表日' else "C9", ascending=False) # 簡易ソート

    st.dataframe(df_sbi, use_container_width=True)

    csv = df_sbi.to_csv(index=False, header=False).encode("utf_8_sig")
    st.download_button(
        label="SBIインポートリストをダウンロード",
        data=csv,
        file_name=f"{dt_now_jst_aware.strftime('%y%m%d')}_rating.csv",
        mime='text/csv',
    )
