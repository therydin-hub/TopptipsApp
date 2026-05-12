import streamlit as st
import pandas as pd
import datetime
import math

# ==========================================
# 1. KONFIGURATION & DESIGN
# ==========================================
st.set_page_config(
    page_title="Pro Football Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS för att göra tabellerna mer lättlästa
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stTable {
        font-size: 12px;
    }
    div[data-testid="stExpander"] {
        background-color: white;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LOGIK (Samma stabila motor som förut)
# ==========================================
def normalize_name(name):
    n = str(name).lower().strip()
    if "celta" in n: return "Celta Vigo"
    if "levante" in n: return "Levante"
    if "ath" in n and ("bilbao" in n or "letic" in n): return "Athletic Bilbao"
    if "nott" in n: return "Nottingham"
    if "man city" in n: return "Man City"
    if "man utd" in n or "man united" in n: return "Man United"
    if "real madrid" in n: return "Real Madrid"
    if "barcelona" in n: return "Barcelona"
    return n.title()

@st.cache_data(ttl=3600)
def get_corner_card_data():
    now = datetime.datetime.now()
    season_str = f"{str(now.year-1)[-2:]}{str(now.year)[-2:]}" if now.month < 8 else f"{str(now.year)[-2:]}{str(now.year+1)[-2:]}"
    
    urls = [
        f"https://www.football-data.co.uk/mmz4281/{season_str}/E0.csv", 
        f"https://www.football-data.co.uk/mmz4281/{season_str}/E1.csv", 
        f"https://www.football-data.co.uk/mmz4281/{season_str}/SP1.csv",
        f"https://www.football-data.co.uk/mmz4281/{season_str}/SP2.csv",
        f"https://www.football-data.co.uk/mmz4281/{season_str}/I1.csv",
        f"https://www.football-data.co.uk/mmz4281/{season_str}/I2.csv",
        "https://www.football-data.co.uk/new/SWE.csv"
    ]

    team_stats = {}
    def init_team(team):
        if team not in team_stats:
            team_stats[team] = {'corners_for': [], 'corners_against': [], 'cards_for': [], 'cards_against': []}

    for url in urls:
        try:
            df = pd.read_csv(url, encoding='unicode_escape', on_bad_lines='skip')
            if 'SWE' in url:
                df['parsed_date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
                df = df[df['parsed_date'].dt.year == now.year]

            for _, row in df.iterrows():
                h_val = row.get('Home') if pd.notna(row.get('Home')) else row.get('HomeTeam')
                a_val = row.get('Away') if pd.notna(row.get('Away')) else row.get('AwayTeam')
                if pd.isna(h_val) or pd.isna(a_val): continue
                
                h, a = normalize_name(str(h_val)), normalize_name(str(a_val))
                init_team(h); init_team(a)

                hc, ac = row.get('HC', 0), row.get('AC', 0)
                hy, hr = row.get('HY', 0), row.get('HR', 0)
                ay, ar = row.get('AY', 0), row.get('AR', 0)
                
                try:
                    team_stats[h]['corners_for'].append(float(hc)); team_stats[h]['corners_against'].append(float(ac))
                    team_stats[a]['corners_for'].append(float(ac)); team_stats[a]['corners_against'].append(float(hc))
                    team_stats[h]['cards_for'].append(float(hy)+float(hr)); team_stats[h]['cards_against'].append(float(ay)+float(ar))
                    team_stats[a]['cards_for'].append(float(ay)+float(ar)); team_stats[a]['cards_against'].append(float(hy)+float(hr))
                except: pass
        except: pass

    return {t: {
        "avg_corners_for": round(sum(d['corners_for'])/len(d['corners_for']), 2),
        "avg_corners_against": round(sum(d['corners_against'])/len(d['corners_against']), 2),
        "avg_cards_for": round(sum(d['cards_for'])/len(d['cards_for']), 2),
        "avg_cards_against": round(sum(d['cards_against'])/len(d['cards_against']), 2)
    } for t, d in team_stats.items() if len(d['corners_for']) > 0}

def poisson_probability(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def format_odds(lam, line):
    prob_under_or_equal = sum(poisson_probability(lam, k) for k in range(math.ceil(line)))
    prob = (1 - prob_under_or_equal) * 100
    if prob <= 0.5: return "0% (-)"
    return f"{round(prob, 1)}% ({round(100/prob, 2)})"

# ==========================================
# 3. ANVÄNDARGRÄNSSNITT (UI)
# ==========================================

with st.sidebar:
    st.header("⚙️ Inställningar")
    st.write("Skriv in dina matcher nedan. En per rad.")
    input_text = st.text_area("Matcher:", value="Arsenal - Everton\nReal Madrid - Barcelona", height=200)
    st.info("Format: Hemmalag - Bortalag")
    calculate_btn = st.button("Kör Analys 🚀", use_container_width=True)

st.title("⚽ Master Stats Predictor")
st.markdown("Baserat på säsongsdata och Poisson-fördelning.")

if calculate_btn:
    stats = get_corner_card_data()
    lines = [l.strip() for l in input_text.split('\n') if " - " in l]
    
    res_corners, res_cards, check_data = [], [], []

    for line in lines:
        try:
            h_raw, a_raw = line.split(" - ")
            h, a = normalize_name(h_raw), normalize_name(a_raw)
            
            if h in stats and a in stats:
                hs, ast = stats[h], stats[a]
                
                # Hörnor
                exp_hc = (hs['avg_corners_for'] + ast['avg_corners_against']) / 2
                exp_ac = (ast['avg_corners_for'] + hs['avg_corners_against']) / 2
                exp_tot_c = exp_hc + exp_ac
                
                # Kort
                exp_h_card = (hs['avg_cards_for'] + ast['avg_cards_against']) / 2
                exp_a_card = (ast['avg_cards_for'] + hs['avg_cards_against']) / 2
                exp_tot_card = exp_h_card + exp_a_card

                # --- ÅTERSTÄLL ALLA KOLUMNER ---
                res_corners.append({
                    'Match': f"{h} vs {a}",
                    'Total Exp': round(exp_tot_c, 1),
                    '>8.5': format_odds(exp_tot_c, 8.5),
                    '>9.5': format_odds(exp_tot_c, 9.5),
                    '>10.5': format_odds(exp_tot_c, 10.5),
                    f'H ({h})': round(exp_hc, 1),
                    '>H 3.5': format_odds(exp_hc, 3.5),
                    '>H 4.5': format_odds(exp_hc, 4.5),
                    '>H 5.5': format_odds(exp_hc, 5.5),
                    f'B ({a})': round(exp_ac, 1),
                    '>B 3.5': format_odds(exp_ac, 3.5),
                    '>B 4.5': format_odds(exp_ac, 4.5),
                    '>B 5.5': format_odds(exp_ac, 5.5)
                })
                
                res_cards.append({
                    'Match': f"{h} vs {a}",
                    'Total Exp': round(exp_tot_card, 1),
                    '>3.5': format_odds(exp_tot_card, 3.5),
                    '>4.5': format_odds(exp_tot_card, 4.5),
                    '>5.5': format_odds(exp_tot_card, 5.5),
                    f'H ({h})': round(exp_h_card, 1),
                    '>H 1.5': format_odds(exp_h_card, 1.5),
                    '>H 2.5': format_odds(exp_h_card, 2.5),
                    '>H 3.5': format_odds(exp_h_card, 3.5),
                    f'B ({a})': round(exp_a_card, 1),
                    '>B 1.5': format_odds(exp_a_card, 1.5),
                    '>B 2.5': format_odds(exp_a_card, 2.5),
                    '>B 3.5': format_odds(exp_a_card, 3.5)
                })
                
                check_data.append({"Lag": h, "Status": "✔️ OK", "Data": stats[h]})
                check_data.append({"Lag": a, "Status": "✔️ OK", "Data": stats[a]})
            else:
                if h not in stats: check_data.append({"Lag": h, "Status": "❌ Saknas", "Data": "-"})
                if a not in stats: check_data.append({"Lag": a, "Status": "❌ Saknas", "Data": "-"})
        except Exception as e:
            st.error(f"Kunde inte tolka raden: {line}")

    # --- VISUALISERING ---
    tab1, tab2, tab3 = st.tabs(["🎯 HÖRN-ANALYS", "🟨 KORT-ANALYS", "🔍 DATAKONTROLL"])
    
    with tab1:
        if res_corners:
            st.subheader("Sannolikhet & Odds för Hörnor")
            st.dataframe(pd.DataFrame(res_corners), use_container_width=True)
        else:
            st.warning("Ingen data hittades för de angivna lagen.")

    with tab2:
        if res_cards:
            st.subheader("Sannolikhet & Odds för Kort")
            st.dataframe(pd.DataFrame(res_cards), use_container_width=True)

    with tab3:
        st.subheader("Hämtad Statistik")
        st.write(pd.DataFrame(check_data))

else:
    st.info("Välkommen! Skriv in dina matcher i sidomenyn till vänster och klicka på 'Kör Analys'.")
