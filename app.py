import streamlit as st
import pandas as pd
import datetime
import math

# ==========================================
# 1. SETUP & DESIGN
# ==========================================
st.set_page_config(page_title="Pro Bet Analyzer", page_icon="⚽", layout="wide")

# Custom CSS för att göra appen snyggare
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    [data-testid="stMetricValue"] { color: #00ff88; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTORN (Datan & Beräkningar)
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
            for _, row in df.iterrows():
                h_val = row.get('Home') if pd.notna(row.get('Home')) else row.get('HomeTeam')
                a_val = row.get('Away') if pd.notna(row.get('Away')) else row.get('AwayTeam')
                if pd.isna(h_val) or pd.isna(a_val): continue
                h, a = normalize_name(str(h_val)), normalize_name(str(a_val))
                init_team(h); init_team(a)
                try:
                    team_stats[h]['corners_for'].append(float(row.get('HC', 0)))
                    team_stats[h]['corners_against'].append(float(row.get('AC', 0)))
                    team_stats[a]['corners_for'].append(float(row.get('AC', 0)))
                    team_stats[a]['corners_against'].append(float(row.get('HC', 0)))
                    team_stats[h]['cards_for'].append(float(row.get('HY', 0))+float(row.get('HR', 0)))
                    team_stats[h]['cards_against'].append(float(row.get('AY', 0))+float(row.get('AR', 0)))
                    team_stats[a]['cards_for'].append(float(row.get('AY', 0))+float(row.get('AR', 0)))
                    team_stats[a]['cards_against'].append(float(row.get('HY', 0))+float(row.get('HR', 0)))
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

def get_prob(lam, line):
    prob_under_or_equal = sum(poisson_probability(lam, k) for k in range(math.ceil(line)))
    return (1 - prob_under_or_equal)

def apply_heatmap(val):
    """Färgkodning för sannolikhet"""
    if isinstance(val, str) and "%" in val:
        num = float(val.replace('%', ''))
        if num >= 65: return 'background-color: #005a32; color: white;' # Grön
        if num >= 50: return 'background-color: #3e5a00; color: white;' # Gul-grön
        if num < 35: return 'background-color: #5a0000; color: white;' # Röd
    return ''

# ==========================================
# 3. ANVÄNDARGRÄNSSNITT
# ==========================================

st.title("⚽ Master Stats Predictor")

with st.sidebar:
    st.header("⚙️ Inställningar")
    input_text = st.text_area("Matcher (t.ex. Arsenal - Everton)", "Arsenal - Everton", height=150)
    
    st.divider()
    st.subheader("💰 Value Checker")
    market_odds = st.number_input("Marknadens Odds (t.ex. Unibet)", value=2.00, step=0.05)
    st.info("Appen jämför >9.5 hörnor mot detta odds för att hitta 'Value'.")
    
    calculate_btn = st.button("ANALYSERA NU 🚀", use_container_width=True)

if calculate_btn:
    stats_db = get_corner_card_data()
    lines = [l.strip() for l in input_text.split('\n') if " - " in l]
    
    res_corners, res_cards = [], []

    for line in lines:
        try:
            h_raw, a_raw = line.split(" - ")
            h, a = normalize_name(h_raw), normalize_name(a_raw)
            
            if h in stats_db and a in stats_db:
                h_s, a_s = stats_db[h], stats_db[a]
                
                # Beräkna Exp Corners
                exp_hc = (h_s['avg_corners_for'] + a_s['avg_corners_against']) / 2
                exp_ac = (a_s['avg_corners_for'] + h_s['avg_corners_against']) / 2
                exp_tot_c = exp_hc + exp_ac
                
                # Sannolikheter
                p85 = get_prob(exp_tot_c, 8.5)
                p95 = get_prob(exp_tot_c, 9.5)
                
                # Value Logik: EV = (Prob * Odds) - 1
                ev = (p95 * market_odds) - 1
                value_label = "✅ BRA" if ev > 0.05 else "❌ NEJ" if ev < -0.05 else "🟡 OK"

                res_corners.append({
                    'Match': f"{h} - {a}",
                    'Exp Tot': round(exp_tot_c, 1),
                    '>8.5 %': f"{round(p85*100, 1)}%",
                    '>9.5 %': f"{round(p95*100, 1)}%",
                    'Ditt Odds': market_odds,
                    'Value (EV)': f"{round(ev*100, 1)}%",
                    'Spelbart?': value_label
                })
        except:
            continue

    # --- VISUALISERING ---
    if res_corners:
        # IDÉ 3: Metric Cards
        col1, col2, col3 = st.columns(3)
        best_ev = max(res_corners, key=lambda x: float(x['Value (EV)'].replace('%','')))
        
        col1.metric("Bästa Value", best_ev['Match'], best_ev['Value (EV)'])
        col2.metric("Högst Sannolikhet (>8.5)", res_corners[0]['Match'], res_corners[0]['>8.5 %'])
        col3.metric("Antal Matcher", len(res_corners))

        st.divider()

        # IDÉ 1: Heatmap Tabell
        st.subheader("🎯 Hörnanalys med Heatmap")
        df = pd.DataFrame(res_corners)
        styled_df = df.style.applymap(apply_heatmap, subset=['>8.5 %', '>9.5 %'])
        st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.error("Kunde inte hitta lagen. Kolla stavningen!")
