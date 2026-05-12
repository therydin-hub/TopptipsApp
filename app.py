import streamlit as st
import pandas as pd
import datetime
import math

# ==========================================
# 1. KONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Football Stats Master", layout="wide")
st.title("🎯 Football Corner & Card Predictor")

# ==========================================
# 2. NAMN-TVÄTTMASKINEN
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

# ==========================================
# 3. RÅDATA-MOTORN (Med Streamlit Cache)
# ==========================================
@st.cache_data(ttl=3600) # Sparar datan i en timme
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
                
                h = normalize_name(str(h_val))
                a = normalize_name(str(a_val))
                init_team(h); init_team(a)

                hc = row.get('HC', 0)
                ac = row.get('AC', 0)
                hy = row.get('HY', 0); hr = row.get('HR', 0)
                ay = row.get('AY', 0); ar = row.get('AR', 0)
                
                try:
                    team_stats[h]['corners_for'].append(float(hc)); team_stats[h]['corners_against'].append(float(ac))
                    team_stats[a]['corners_for'].append(float(ac)); team_stats[a]['corners_against'].append(float(hc))
                    team_stats[h]['cards_for'].append(float(hy)+float(hr)); team_stats[h]['cards_against'].append(float(ay)+float(ar))
                    team_stats[a]['cards_for'].append(float(ay)+float(ar)); team_stats[a]['cards_against'].append(float(hy)+float(hr))
                except: pass
        except: pass

    final_stats = {team: {
        "avg_corners_for": round(sum(d['corners_for'])/len(d['corners_for']), 2),
        "avg_corners_against": round(sum(d['corners_against'])/len(d['corners_against']), 2),
        "avg_cards_for": round(sum(d['cards_for'])/len(d['cards_for']), 2),
        "avg_cards_against": round(sum(d['cards_against'])/len(d['cards_against']), 2)
    } for team, d in team_stats.items() if len(d['corners_for']) > 0}
    
    return final_stats

# ==========================================
# 4. MATEMATIKFUNKTIONER
# ==========================================
def poisson_probability(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def format_odds(lam, line):
    prob_under_or_equal = sum(poisson_probability(lam, k) for k in range(math.ceil(line)))
    prob = (1 - prob_under_or_equal) * 100
    if prob <= 0.5: return "0% (-)"
    return f"{round(prob, 1)}% ({round(100/prob, 2)})"

# ==========================================
# 5. STREAMLIT UI
# ==========================================
input_text = st.text_area("Skriv in matcher (t.ex: Arsenal - Liverpool)", height=150)
calculate_btn = st.button("Generera Master-Tabell 🚀")

if calculate_btn and input_text:
    stats = get_corner_card_data()
    lines = [l.strip() for l in input_text.split('\n') if " - " in l]
    
    res_corners, res_cards, check_data = [], [], []

    for line in lines:
        h_raw, a_raw = line.split(" - ")
        h, a = normalize_name(h_raw), normalize_name(a_raw)
        
        # Check team existence
        for team in [h, a]:
            if team in stats:
                s = stats[team]
                check_data.append({"Lag": team, "Hörnor F/E": f"{s['avg_corners_for']}/{s['avg_corners_against']}", "Status": "✔️ OK"})
            else:
                check_data.append({"Lag": team, "Status": "❌ Saknas"})

        if h in stats and a in stats:
            hs, ast = stats[h], stats[a]
            exp_hc = (hs['avg_corners_for'] + ast['avg_corners_against']) / 2
            exp_ac = (ast['avg_corners_for'] + hs['avg_corners_against']) / 2
            
            exp_h_card = (hs['avg_cards_for'] + ast['avg_cards_against']) / 2
            exp_a_card = (ast['avg_cards_for'] + hs['avg_cards_against']) / 2

            res_corners.append({
                'Match': f"{h} vs {a}",
                'Tot Exp': round(exp_hc + exp_ac, 1),
                '>8.5': format_odds(exp_hc + exp_ac, 8.5),
                '>9.5': format_odds(exp_hc + exp_ac, 9.5),
                f'{h} >4.5': format_odds(exp_hc, 4.5),
                f'{a} >4.5': format_odds(exp_ac, 4.5)
            })
            
            res_cards.append({
                'Match': f"{h} vs {a}",
                'Tot Exp': round(exp_h_card + exp_a_card, 1),
                '>3.5': format_odds(exp_h_card + exp_a_card, 3.5),
                '>4.5': format_odds(exp_h_card + exp_a_card, 4.5),
                f'{h} >1.5': format_odds(exp_h_card, 1.5),
                f'{a} >1.5': format_odds(exp_a_card, 1.5)
            })

    # Display results in tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Hörnor", "🟨 Kort", "🔍 Datakontroll"])
    with tab1: st.table(pd.DataFrame(res_corners))
    with tab2: st.table(pd.DataFrame(res_cards))
    with tab3: st.dataframe(pd.DataFrame(check_data))
