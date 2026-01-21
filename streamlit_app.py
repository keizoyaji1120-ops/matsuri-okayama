import streamlit as st
import pandas as pd
import json
import urllib.request
import urllib.parse
import datetime
import math
import ssl
import matplotlib.pyplot as plt
import warnings

# --- 設定 ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="魔釣 - 岡山・下津井タイラバ予報 v1.7", page_icon="🍑")

# --- CSS (デザイン設定) ---
st.markdown("""
    <style>
    /* 岡山版スペシャル：背景を薄ピンク（ピーチホワイト）に */
    .stApp {
        background-color: #fff5f7;
    }

    /* 静的テーブルのデザイン */
    table.matsuri-table {
        width: 100%;
        border-collapse: collapse;
        font-family: "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif;
        font-size: 13px;
        color: #333;
        margin-bottom: 20px;
        background-color: #ffffff;
    }
    table.matsuri-table th {
        background-color: #ffe6eb;
        color: #31333F;
        font-weight: bold;
        padding: 10px 4px;
        text-align: center;
        border-bottom: 2px solid #ffccd5;
        white-space: nowrap;
    }
    table.matsuri-table td {
        padding: 8px 4px;
        text-align: center;
        border-bottom: 1px solid #eee;
        vertical-align: middle;
        line-height: 1.5;
    }
    table.matsuri-table tr:nth-child(even) {
        background-color: #fffbfb;
    }
    
    /* 列ごとの幅とスタイル */
    .col-time { width: 18%; font-weight: bold; font-size: 12px; white-space: nowrap; }
    .col-honmei { width: 22%; color: #d63031; font-weight: bold; }
    .col-osae { width: 22%; color: #0984e3; }
    .col-tac { width: 18%; font-size: 12px; }
    .col-note { width: 20%; font-size: 11px; text-align: left; color: #666; }
    
    /* スマホ表示時の微調整 */
    @media (max-width: 640px) {
        table.matsuri-table { font-size: 11px; }
        .col-time { font-size: 10px; }
        .col-tac { font-size: 10px; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 定数（岡山・下津井エリア設定） ---
OKAYAMA_LAT = 34.43
OKAYAMA_LON = 133.80

HISTORICAL_TEMPS = {
    1: 9.5, 2: 9.0, 3: 10.0, 4: 13.5, 5: 18.0, 6: 22.0,
    7: 26.5, 8: 28.0, 9: 26.0, 10: 22.5, 11: 17.5, 12: 13.0
}

KAIHO_URL = "https://www6.kaiho.mlit.go.jp/bisan/currenttide.html"
SEAT_CHECKER_URL = "" 

# --- 関数群 ---
@st.cache_data(ttl=3600)
def make_request(url):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (App; CPU iPhone OS 15_0)')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx) as res:
            return json.loads(res.read().decode())
    except:
        return None

def get_moon_age(date):
    year, month, day = date.year, date.month, date.day
    if month < 3: year -= 1; month += 12
    p = math.floor(year / 4)
    age = (year + p + month * 9 / 25 + day + 11) % 30
    return int(age)

def get_sinker_fixed():
    return {
        "15m": "30g",
        "20m": "30g",
        "30m": "45g",
        "45m": "60g"
    }

def estimate_okayama_tide(moon_age, hour):
    base_high = 9.0; delay = 0.8
    high_tide = (base_high + (moon_age % 15) * delay) % 12
    diff = abs(hour - high_tide)
    if diff > 6: diff = 12 - diff
    level = math.cos(diff * (math.pi / 6))
    is_slack = (diff < 1.0 or abs(diff - 6.0) < 1.0)
    return level, is_slack

def get_seasonal_bait(month):
    if month in [12, 1, 2, 3]:
        return "海苔・アミ", "定番ピンク・黒・緑"
    elif month in [4, 5]:
        return "真鯛の乗っ込み", "赤オレ・オレンジ・ピンク"
    elif month in [6, 7, 8]:
        return "イワシ・イカ", "ゴールド・チャート・グロー"
    elif month in [9, 10, 11]:
        return "広範囲ベイト", "赤オレ・オレンジ・エビオレ"
    else:
        return "混合", "赤オレ"

def suggest_strategy(h, sun_h, sc, t_diff, month, temp, cloud_cover, rain, is_slack):
    """
    岡山・下津井特化ロジック v1.7
    - 浅場対策：キャスティング推奨
    - 潮止まり：アコウ推奨
    """
    c1 = "赤オレ"
    s1 = "カーリー"
    speed = "普通"
    hook = "S"

    # --- ネクタイカラー選定 ---
    is_low_light = (h <= sun_h) or (cloud_cover > 70) or (rain >= 0.5)
    
    if rain >= 0.5:
        c1 = "チャート" if h % 2 == 0 else "シマシマピンク"
    elif h <= sun_h:
        c1 = "ゴールド" if h % 2 == 0 else "蛍光ピンク"
    elif t_diff <= -0.5:
        c1 = "レッド" if h % 2 == 0 else "黒/海苔"
    elif month in [12, 1, 2, 3] and (temp < 12.0):
        c1 = "シマシマオレンジ" if h % 2 == 0 else "海苔グリーン"
    elif is_low_light:
        c1 = "チャート" if h % 2 == 0 else "赤オレ"
    else:
        rem = h % 3
        if rem == 0:
            c1 = "定番ピンク"
        elif rem == 1:
            c1 = "赤オレ"
        else:
            c1 = "オレンジゼブラ"
    
    # --- 形状選定 ---
    if rain >= 0.5:
        s1 = "ワイド強波動"
    elif sc >= 50: 
        s1 = "極太ビッグ"
    elif sc >= 30: 
        s1 = "ビッグカーリー"
    elif sc >= 15:
        s1 = "ショートカーリー"
    else:
        s1 = "ストレート"
    
    # --- 巻き速度 ---
    if temp >= 18.0 and sc >= 40:
        speed = "早巻"
    elif temp <= 10.0:
        speed = "デッドスロー"
    elif temp <= 12.0 or sc <= 20:
        speed = "激遅"
    elif sc >= 30:
        speed = "普通"
    else:
        speed = "遅め"

    # --- フックサイズ ---
    if s1 == "極太ビッグ":
        hook = "L"
    elif month in [1, 2] and temp < 10.0:
        hook = "3S"
    elif month in [12, 1, 2, 3] or temp < 12.0:
        hook = "SS"
    elif sc >= 60 and temp >= 18.0:
        hook = "M"
    else:
        hook = "S"

    # --- 戦術オプション（キャスティング/ワーム/アコウ） ---
    tactics_note = ""
    
    # 潮が緩い or 浅場想定 -> キャスト推奨
    if sc < 40 and not is_slack:
        tactics_note = "投(キャスト)"
    
    # 潮止まり -> アコウチャンス
    if is_slack and temp > 12.0: # 極寒期以外
        tactics_note = "底(アコウ)"

    # --- 抑えパターン ---
    if c1 == "定番ピンク": c2 = "赤オレ"
    elif c1 == "赤オレ": c2 = "オレンジゼブラ"
    elif c1 == "オレンジゼブラ": c2 = "海老茶"
    elif c1 == "チャート": c2 = "ゴールド"
    elif "黒" in c1: c2 = "コーラ"
    elif "レッド" in c1: c2 = "オレンジ"
    else: c2 = "赤オレ"
    
    # 形状ローテ
    if "ビッグ" in s1 or "強波動" in s1:
        s2 = "ショート"
    elif "ショート" in s1:
        s2 = "極細ストレート"
    else:
        s2 = "カーリー"
    
    return f"{c1}×{s1}", f"{c2}×{s2}", speed, hook, tactics_note

@st.cache_data(ttl=3600)
def get_weather_data(target_date):
    bm = "https://marine-api.open-meteo.com/v1/marine"
    bw = "https://api.open-meteo.com/v1/forecast"
    d_str = target_date.strftime("%Y-%m-%d")
    y_str = (target_date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    p_temp = {"latitude": OKAYAMA_LAT, "longitude": OKAYAMA_LON, "hourly": "sea_surface_temperature", "start_date": y_str, "end_date": d_str}
    
    p_weather = {
        "latitude": OKAYAMA_LAT, 
        "longitude": OKAYAMA_LON, 
        "daily": "sunrise", 
        "hourly": "cloud_cover,wind_speed_10m,rain",
        "start_date": d_str, 
        "end_date": d_str, 
        "timezone": "Asia/Tokyo"
    }
    
    return make_request(f"{bm}?{urllib.parse.urlencode(p_temp)}"), make_request(f"{bw}?{urllib.parse.urlencode(p_weather)}")

# --- メイン画面 ---
def main():
    st.markdown("""
        <h1 style='text-align: center; font-size: 32px; margin-bottom: 10px; font-weight: 800;'>
            <span style='margin-right: 0.5em;'>🍑 魔釣</span><br>
            <span style='font-size: 24px; font-weight: normal;'>岡山・下津井タイラバ予報</span>
        </h1>
        <p style='text-align: center; font-size: 13px; color: gray; margin-bottom: 20px;'>
            備讃瀬戸の潮流・水温・独自カラー理論から<br>
            <b>「攻め時」</b>と<b>「ビッグネクタイ戦略」</b>を解析します。
        </p>
    """, unsafe_allow_html=True)

    target_date = st.date_input("釣行日を選択してください", datetime.date.today() + datetime.timedelta(days=1))
    
    bait_name, bait_colors = get_seasonal_bait(target_date.month)
    st.info(f"🐟 **現在のシーズナルパターン: {bait_name}**\n\n有効カラー目安: {bait_colors}")

    if st.button("魔釣予報を開始する"):
        try:
            with st.spinner('瀬戸大橋周辺の海況を解析中...'):
                mage = get_moon_age(target_date)
                
                # 月齢による潮名判定
                age_norm = mage % 15
                if age_norm <= 2 or age_norm >= 13: tide_name = "大潮(激)"
                elif 3 <= age_norm <= 5 or 10 <= age_norm <= 12: tide_name = "中潮(速)"
                else: tide_name = "小潮(緩)"

                sinker_dict = get_sinker_fixed()
                
                sd, wd = get_weather_data(target_date)
                sun_h = int(wd["daily"]["sunrise"][0].split('T')[1].split(':')[0]) if wd else 7
                
                r_temps = sd["hourly"]["sea_surface_temperature"] if sd else []
                r_clouds = wd["hourly"]["cloud_cover"] if (wd and "cloud_cover" in wd["hourly"]) else []
                r_winds = wd["hourly"]["wind_speed_10m"] if (wd and "wind_speed_10m" in wd["hourly"]) else []
                r_rains = wd["hourly"]["rain"] if (wd and "rain" in wd["hourly"]) else []
                
                OFF = 15
                use_historical = False
                valid_data_list = [t for t in r_temps if t is not None and t > 0]
                
                day_trend_score = 0
                day_trend_label = ""

                if not valid_data_list:
                    use_historical = True
                    avg_temp = HISTORICAL_TEMPS.get(target_date.month, 15.0)
                    r_temps = [avg_temp] * 48
                else:
                    if len(r_temps) >= 48:
                        temps_yesterday = [t for t in r_temps[0:24] if t is not None]
                        temps_today = [t for t in r_temps[24:48] if t is not None]

                        if temps_yesterday and temps_today:
                            avg_yesterday = sum(temps_yesterday) / len(temps_yesterday)
                            avg_today = sum(temps_today) / len(temps_today)
                            diff_day = avg_today - avg_yesterday
                            
                            if diff_day <= -0.5:
                                day_trend_score = -20
                                day_trend_label = "⚠️前日比↓"
                            elif diff_day >= 0.5:
                                day_trend_score = 10
                                day_trend_label = "前日比↑"

                day_temps = []
                for h in range(5, 16):
                    idx = OFF + h
                    if idx < len(r_temps) and r_temps[idx] is not None:
                         day_temps.append(r_temps[idx])
                
                min_t = min(day_temps) if day_temps else 0
                max_t = max(day_temps) if day_temps else 0

                st.success("解析完了！")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="月齢・潮回り", value=f"{mage:.1f}", delta=tide_name)
                with col2:
                    st.markdown(f"""
                    **推奨シンカー (水深固定)**
                    - **15m**: {sinker_dict['15m']}
                    - **30m**: {sinker_dict['30m']}
                    - **45m**: {sinker_dict['45m']}
                    """, unsafe_allow_html=True)
                    st.caption("※ビッグネクタイ使用時は+1ランク重くしてください。")
                
                if use_historical:
                    st.info(f"⚠️ 長期予報のため、平年値（約{min_t}℃）を使用しています。")
                else:
                    st.info(f"🌡️ 水温範囲: {min_t:.1f}℃ 〜 {max_t:.1f}℃")
                    if day_trend_label == "⚠️前日比↓":
                         st.warning("⚠️ 前日より水温が平均0.5℃以上低下しています。活性ダウンに注意。")
                    elif day_trend_label == "前日比↑":
                         st.info("📈 前日より水温が上昇傾向です。好活性に期待！")

                hl, sl, tl, tll = [], [], [], []
                
                table_html_rows = ""
                
                for h in range(5, 16):
                    idx = OFF + h
                    ct = r_temps[idx] if (idx < len(r_temps) and r_temps[idx] is not None) else (day_temps[0] if day_temps else 15.0)
                    pt = ct
                    if idx > 0 and r_temps[idx-1] is not None:
                        pt = r_temps[idx-1]
                    
                    tdiff = ct - pt
                    if use_historical: tdiff = 0
                    
                    cloud = r_clouds[h] if (h < len(r_clouds) and r_clouds[h] is not None) else 0
                    wind = r_winds[h] if (h < len(r_winds) and r_winds[h] is not None) else 0
                    rain = r_rains[h] if (h < len(r_rains) and r_rains[h] is not None) else 0
                    
                    tlev, slack = estimate_okayama_tide(mage, h)
                    
                    # --- スコア計算（岡山甘口＆水温厳格版） ---
                    sc = 40 # 基礎点
                    
                    if h == sun_h: sc += 30
                    if slack: sc += 40 
                    elif h>5 and abs(tlev - tll[-1]) > 0.3: sc += 30
                    
                    if not use_historical:
                        if tdiff >= 0.1: sc += 20
                        elif tdiff <= -0.1: sc -= 20
                    
                    sc += day_trend_score
                    
                    w_icon = ""
                    if rain >= 0.5:
                        sc += 10; w_icon = "☔"
                    elif cloud >= 60: 
                        sc += 10; w_icon = "☁️"
                    elif cloud <= 20:
                        sc -= 5; w_icon = "☀️"
                    else:
                        w_icon = "⛅"
                    
                    wind_text = ""
                    if wind >= 10.0:
                        sc = 0; wind_text = "爆風"
                    elif wind >= 7.0:
                        sc -= 10; wind_text = "強風"
                    elif wind >= 5.0:
                        sc += 5; wind_text = "やや強"
                    elif wind >= 2.0:
                        sc += 20; wind_text = "最適"
                    else:
                        sc -= 20; wind_text = "静穏"
                    
                    low_temp_alert = ""
                    if ct <= 10.0:
                        sc = int(sc * 0.2); low_temp_alert = "激渋"
                    elif ct <= 12.0:
                        sc = int(sc * 0.5); low_temp_alert = "低水温"
                    
                    if sc < 0: sc = 0
                    if sc > 100: sc = 100
                    
                    # 戦術にis_slackを渡す
                    tie1, tie2, spd, hk, tactics = suggest_strategy(h, sun_h, sc, tdiff, target_date.month, ct, cloud, rain, slack)
                    
                    time_display = f"{h}:00<br>{w_icon} {wind_text}"
                    tac_display = f"{spd}・{hk}"
                    # 戦術（キャスト/アコウ）がある場合は表示
                    if tactics: tac_display += f"<br><span style='color:#d63031; font-weight:bold;'>{tactics}</span>"

                    notes = []
                    if slack: notes.append("★転流")
                    if low_temp_alert: notes.append(f"⚠️{low_temp_alert}")
                    if rain >= 0.5: notes.append("濁り")
                    if day_trend_label and not low_temp_alert: notes.append(day_trend_label)
                    note_str = " ".join(notes)
                    
                    hl.append(h); sl.append(sc); tl.append(ct); tll.append(tlev)
                    
                    row_html = f"<tr><td class='col-time'>{time_display}</td><td class='col-honmei'>{tie1}</td><td class='col-osae'>{tie2}</td><td class='col-tac'>{tac_display}</td><td class='col-note'>{note_str}</td></tr>"
                    table_html_rows += row_html

                # --- グラフ描画 ---
                TITLE_SIZE = 18; LABEL_SIZE = 14; TICK_SIZE = 12; LINE_WIDTH = 2.5; MARKER_SIZE = 8

                title_txt = f"{target_date} Okayama Forecast (Moon:{mage:.1f})"
                fig, ax1 = plt.subplots(figsize=(10, 6))
                
                color = 'tab:blue'
                ax1.set_xlabel('Time', fontsize=LABEL_SIZE)
                ax1.set_ylabel('Score', color=color, fontsize=LABEL_SIZE)
                ax1.bar(hl, sl, color=color, alpha=0.4)
                ax1.set_ylim(0, 100)
                ax1.tick_params(axis='x', labelsize=TICK_SIZE)
                ax1.tick_params(axis='y', labelcolor=color, labelsize=TICK_SIZE)
                
                ax2 = ax1.twinx()
                color = 'tab:red'
                ax2.set_ylabel('Temp (C)', color=color, fontsize=LABEL_SIZE)
                ax2.plot(hl, tl, color=color, marker='o', linewidth=LINE_WIDTH, markersize=MARKER_SIZE)
                vt = [t for t in tl if t > 0]
                if vt:
                     margin = 1.0 if max(vt) == min(vt) else 0.5
                     ax2.set_ylim(min(vt)-margin, max(vt)+margin)
                ax2.tick_params(axis='y', labelcolor=color, labelsize=TICK_SIZE)
                
                ax3 = ax1.twinx()
                ax3.spines["right"].set_position(("axes", 1.15))
                color = 'tab:green'
                ax3.set_ylabel('Tide (Est)', color=color, fontsize=LABEL_SIZE)
                ax3.plot(hl, tll, color=color, linestyle='--', marker='x', linewidth=LINE_WIDTH, markersize=MARKER_SIZE)
                ax3.set_ylim(-1.5, 1.5)
                ax3.set_yticks([])
                
                plt.title(title_txt, fontsize=TITLE_SIZE)
                plt.grid(axis='x', linestyle='--', alpha=0.5)
                st.pyplot(fig)

                st.markdown("### 📝 定番カラー戦略 & ビッグネクタイ判定", unsafe_allow_html=True)
                
                full_table_html = f"""
                <table class="matsuri-table">
                    <thead>
                        <tr>
                            <th>時間<br>(天気/風)</th>
                            <th>本命(定番)</th>
                            <th>抑え</th>
                            <th>戦術<br>(速/針/他)</th>
                            <th>備考</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_html_rows}
                    </tbody>
                </table>
                """
                st.markdown(full_table_html, unsafe_allow_html=True)
                
                st.caption("※時間の「★」は転流（潮止まり）の目安です。")
                
                st.markdown("""
                <div style="font-size: 12px; color: gray; margin-bottom: 10px;">
                <strong>【風速の目安】</strong><br>
                🌪️ <strong>爆風</strong>：出船中止レベル (10m以上)<br>
                🌬️ <strong>強風</strong>：瀬戸大橋下は危険 (7m〜)<br>
                🍃 <strong>最適</strong>：程よく船が流れる (2m〜)<br>
                🌊 <strong>静穏</strong>：船が流れず苦戦 (2m未満)
                </div>
                """, unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("🔗 関連ツール")
                
                col_link1, col_link2 = st.columns(2)
                
                with col_link1:
                    st.markdown("##### 🌊 公式データ")
                    st.link_button("備讃瀬戸の潮流情報", KAIHO_URL)
                    
                with col_link2:
                    st.markdown("##### 🚤 釣り座")
                    st.write("Coming Soon...")

                st.markdown("---")
                st.markdown("""
                <div style='background-color: #f0f2f6; padding: 15px; border-radius: 5px; color: #555; font-size: 12px;'>
                    <strong>【⚠️ 免責事項・利用規約】</strong><br><br>
                    <strong>1. 情報の正確性</strong><br>
                    本アプリの予報は独自の計算ロジックに基づく推測値であり、実際の気象・海況とは異なる場合があります。<br><br>
                    <strong>2. 安全の確保（重要）</strong><br>
                    出船の可否や現場での安全判断については、必ず<strong>海上保安庁の警報</strong>や<strong>船長の指示</strong>を最優先してください。<br>
                    本アプリを航海用海図（ナビゲーション）の代わりに使用することは絶対にお止めください。<br><br>
                    <strong>3. 責任の所在</strong><br>
                    本アプリの利用に起因するいかなる損失・損害についても、開発者は一切の責任を負わず、補償等は行いません。<br><br>
                    <strong>4. 営利利用の禁止</strong><br>
                    本アプリのデータを<strong>第三者へ販売、再配布、または営利目的で利用することを固く禁じます。</strong><br>
                    本アプリは個人の趣味の範囲でご利用ください。<br><br>
                    <div style='text-align: right; margin-top: 10px;'>
                        <a href="https://open-meteo.com/" target="_blank" style="text-decoration: none; color: #555;">Weather data by Open-Meteo.com</a><br>
                        © 2026 魔釣 - Matsuri Fishing Forecast (Okayama Edition)
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"予期せぬエラーが発生しました: {e}")
            st.warning("日付を変更するか、しばらく時間を置いてから再度お試しください。")

if __name__ == "__main__":
    main()
