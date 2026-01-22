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
st.set_page_config(page_title="魔釣 - 岡山・下津井タイラバ予報 v1.8", page_icon="🍑", layout="centered")

# --- CSS (プレミアムデザイン設定) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&family=Roboto:wght@500;700&display=swap');

    /* 全体の背景：桃色グラデーション */
    .stApp {
        background: linear-gradient(180deg, #fff0f5 0%, #ffffff 100%);
        font-family: 'Noto Sans JP', sans-serif;
    }

    /* タイトルロゴ風デザイン */
    .title-logo {
        font-family: 'Noto Sans JP', sans-serif;
        font-weight: 900;
        font-size: 2.2rem;
        background: linear-gradient(45deg, #ff6b81, #ff9f43);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 0;
    }
    
    .subtitle {
        font-size: 0.9rem;
        color: #777;
        margin-top: -10px;
        margin-bottom: 20px;
        font-weight: 500;
    }

    /* カード（グラスモーフィズム） */
    .glass-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.8);
        box-shadow: 0 8px 32px 0 rgba(255, 105, 135, 0.10);
        padding: 20px;
        margin-bottom: 20px;
    }

    /* 注目情報の強調 */
    .highlight-box {
        background: linear-gradient(135deg, #fff5f7 0%, #ffeef2 100%);
        border-left: 5px solid #ff6b81;
        padding: 15px;
        border-radius: 8px;
        color: #444;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* テーブルデザイン（モダン） */
    table.matsuri-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        font-family: 'Roboto', 'Noto Sans JP', sans-serif;
        font-size: 13px;
        color: #333;
        margin-bottom: 20px;
        background-color: #ffffff;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    table.matsuri-table th {
        background: linear-gradient(to bottom, #ffe6eb, #ffccd5);
        color: #444;
        font-weight: 700;
        padding: 12px 6px;
        text-align: center;
        border-bottom: 1px solid #ffccd5;
        white-space: nowrap;
    }
    table.matsuri-table td {
        padding: 10px 6px;
        text-align: center;
        border-bottom: 1px solid #f0f0f0;
        vertical-align: middle;
        line-height: 1.4;
        transition: background-color 0.2s;
    }
    /* 行のホバーエフェクト */
    table.matsuri-table tr:hover td {
        background-color: #fff0f5;
    }
    table.matsuri-table tr:last-child td {
        border-bottom: none;
    }

    /* 列ごとのスタイル */
    .col-time { width: 15%; font-weight: bold; font-size: 12px; color: #555; }
    .col-honmei { width: 25%; color: #d63031; font-weight: bold; font-size: 14px; }
    .col-osae { width: 25%; color: #0984e3; font-size: 13px; }
    .col-tac { width: 15%; font-size: 12px; font-weight: 500; }
    .col-note { width: 20%; font-size: 11px; text-align: left; color: #666; }

    /* ボタンのカスタマイズ */
    div.stButton > button {
        background: linear-gradient(45deg, #ff6b81, #ff4757);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 10px 24px;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(255, 71, 87, 0.3);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(255, 71, 87, 0.4);
    }

    /* スマホ調整 */
    @media (max-width: 640px) {
        table.matsuri-table { font-size: 11px; }
        .col-time { font-size: 10px; }
        .col-tac { font-size: 10px; }
        .col-honmei { font-size: 12px; }
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
    岡山・下津井特化ロジック v1.7ベース
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

    # --- 戦術オプション ---
    tactics_note = ""
    if sc < 40 and not is_slack:
        tactics_note = "投(キャスト)"
    if is_slack and temp > 12.0:
        tactics_note = "底(アコウ)"

    # --- 抑えパターン ---
    if c1 == "定番ピンク": c2 = "赤オレ"
    elif c1 == "赤オレ": c2 = "オレンジゼブラ"
    elif c1 == "オレンジゼブラ": c2 = "海老茶"
    elif c1 == "チャート": c2 = "ゴールド"
    elif "黒" in c1: c2 = "コーラ"
    elif "レッド" in c1: c2 = "オレンジ"
    else: c2 = "赤オレ"
    
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
    # ヘッダー（カスタムHTMLでかっこよく）
    st.markdown("""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h1 class="title-logo">🍑 MATSURI <span style='font-size:1.5rem; color:#444;'>OKAYAMA</span></h1>
            <p class="subtitle">魔釣・下津井タイラバ予報 | 潮流×独自理論</p>
        </div>
    """, unsafe_allow_html=True)

    # カード1: 日付選択とシーズナルパターン
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    col_d, col_info = st.columns([1, 2])
    
    with col_d:
        target_date = st.date_input("釣行日", datetime.date.today() + datetime.timedelta(days=1))
    
    bait_name, bait_colors = get_seasonal_bait(target_date.month)
    with col_info:
        st.markdown(f"""
        <div class="highlight-box">
            <strong>🐟 SEASONAL: {bait_name}</strong><br>
            <span style='font-size:13px; color:#666;'>有効カラー: {bait_colors}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🌊 予報を解析する"):
        try:
            with st.spinner('瀬戸大橋の潮を解析中...'):
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
                
                # --- 結果表示 ---
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                
                # メトリクス表示
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("月齢", f"{mage:.1f}", tide_name)
                
                if use_historical:
                    m_col2.metric("推測水温", f"約{min_t}℃", "平年値")
                else:
                    delta_t = f"{diff_day:+.1f}℃" if 'diff_day' in locals() else None
                    m_col2.metric("水温", f"{min_t:.1f}℃", delta_t)
                
                m_col3.metric("天気", "解析済", "風/雨/雲")
                
                st.markdown("---")
                
                # シンカー情報
                st.markdown(f"""
                <div style='text-align: center; font-size: 13px; color: #555;'>
                    <strong>⚓ 推奨シンカー (水深目安)</strong><br>
                    15m:<b>{sinker_dict['15m']}</b> / 
                    30m:<b>{sinker_dict['30m']}</b> / 
                    45m:<b>{sinker_dict['45m']}</b><br>
                    <span style='font-size:11px; color:#888;'>※ビッグネクタイ使用時は+1ランク重く</span>
                </div>
                """, unsafe_allow_html=True)
                
                if day_trend_label == "⚠️前日比↓":
                     st.warning("⚠️ 前日より水温が低下しています。活性ダウンに注意。")
                
                st.markdown('</div>', unsafe_allow_html=True)

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
                    
                    # --- スコア計算 ---
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
                    
                    tie1, tie2, spd, hk, tactics = suggest_strategy(h, sun_h, sc, tdiff, target_date.month, ct, cloud, rain, slack)
                    
                    time_display = f"{h}:00<br>{w_icon} {wind_text}"
                    tac_display = f"{spd}・{hk}"
                    if tactics: tac_display += f"<br><span style='color:#ff4757; font-weight:bold;'>{tactics}</span>"

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
                TITLE_SIZE = 14; LABEL_SIZE = 10; TICK_SIZE = 9
                title_txt = f"{target_date} Okayama Forecast (Moon:{mage:.1f})"
                
                # グラフ背景を透明にしてデザインに馴染ませる
                fig, ax1 = plt.subplots(figsize=(10, 5))
                fig.patch.set_alpha(0) 
                ax1.patch.set_alpha(0)
                
                color = '#0984e3'
                ax1.set_ylabel('Score', color=color, fontsize=LABEL_SIZE)
                ax1.bar(hl, sl, color=color, alpha=0.3, label='Score')
                ax1.set_ylim(0, 100)
                ax1.tick_params(axis='y', labelcolor=color, labelsize=TICK_SIZE)
                
                ax2 = ax1.twinx()
                color = '#d63031'
                ax2.set_ylabel('Temp (C)', color=color, fontsize=LABEL_SIZE)
                ax2.plot(hl, tl, color=color, marker='o', linewidth=2, markersize=6, label='Temp')
                
                vt = [t for t in tl if t > 0]
                if vt:
                     margin = 1.0 if max(vt) == min(vt) else 0.5
                     ax2.set_ylim(min(vt)-margin, max(vt)+margin)
                ax2.tick_params(axis='y', labelcolor=color, labelsize=TICK_SIZE)
                
                plt.title(title_txt, fontsize=TITLE_SIZE)
                plt.grid(axis='x', linestyle='--', alpha=0.3)
                
                st.pyplot(fig)

                st.markdown("### 📝 時間別攻略データ", unsafe_allow_html=True)
                
                full_table_html = f"""
                <div style="overflow-x:auto;">
                <table class="matsuri-table">
                    <thead>
                        <tr>
                            <th>時間</th>
                            <th>本命</th>
                            <th>抑え</th>
                            <th>戦術</th>
                            <th>備考</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_html_rows}
                    </tbody>
                </table>
                </div>
                """
                st.markdown(full_table_html, unsafe_allow_html=True)
                
                st.caption("※「投」=キャスティング推奨、「底」=潮止まりアコウ狙い")

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
                <div style='background-color: #fff0f5; padding: 15px; border-radius: 8px; color: #666; font-size: 11px; border: 1px solid #ffccd5;'>
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
