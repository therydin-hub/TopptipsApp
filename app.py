import streamlit as st
import pandas as pd
import datetime
import math

# ==========================================
# 1. SETUP & STYLE
# ==========================================
st.set_page_config(page_title="Pro Bet Analyzer", layout="wide")

# CSS för att skapa "betting-vibbar" och snygga tabeller
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #00ff88; }
    .stDataFrame { border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTORN (Beräkningar)
# ==========================================
def poisson_probability(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def get_prob(lam, line):
    prob_under_or_equal = sum(poisson_probability(lam, k) for k in range(math.ceil(line)))
    return (1 - prob_under_or_equal)

def color_value(val):
    """Färgar celler baserat på Expected Value (EV)"""
    if isinstance(val, str) and "%" in val:
        prob = float(val.split("%")[0]) / 100
        # Här kan vi lägga till logik om vi jämför mot ett odds
        if prob > 0.7: return 'background-color: #004d26; color: white' # Mörkgrön
        if prob > 0.6: return 'background-color: #008040; color: white' # Grön
        if prob < 0.4: return 'background-color: #4d0000; color: white' # Röd
    return ''

# [Här behålls normalize_name och get_corner_card_data från din tidigare kod]
# (Jag utelämnar dem här för att spara plats, men de ska ligga kvar i din fil)

# ==========================================
# 3. UI - DASHBOARD
# ==========================================
st.title("📊 Football Value Finder")

with st.sidebar:
    st.header("1. Input")
    input_matches = st.text_area("Matcher (Hemmalag - Bortalag)", "Arsenal - Everton", height=150)
    
    st.header("2. Marknadens Odds")
    market_odds = st.number_input("Ditt odds (för Value-kalkyl)", value=2.0, step=0.1)
    
    analyze_btn = st.button("KÖR ANALYS 🚀", use_container_width=True)

if analyze_btn:
    stats_db = get_corner_card_data() # Din befintliga funktion
    matches = [m.strip() for m in input_matches.split('\n') if " - " in m]
    
    all_corners = []
    top_picks = []

    for match in matches:
        h_n, a_n = [normalize_name(x) for x in match.split(" - ")]
        
        if h_n in stats_db and a_n in stats_db:
            h_s, a_s = stats_db[h_n], stats_db[a_n]
            
            # Beräkna Exp
            exp_tot = (h_s['avg_corners_for'] + a_s['avg_corners_against'] + a_s['avg_corners_for'] + h_s['avg_corners_against']) / 2
            
            # Sannolikheter
            p85 = get_prob(exp_tot, 8.5)
            p95 = get_prob(exp_tot, 9.5)
            
            # Value-kalkyl mot marknadens odds
            ev = (p95 * market_odds) - 1
            
            res = {
                "Match": f"{h_n} - {a_n}",
                "Exp Tot": round(exp_tot, 2),
                ">8.5 (%)": f"{round(p85*100, 1)}%",
                ">9.5 (%)": f"{round(p95*100, 1)}%",
                "Value (EV)": f"{round(ev*100, 1)}%"
            }
            all_corners.append(res)
            if ev > 0.05: top_picks.append(f"{res['Match']} (>9.5)")

    # --- IDÉ 3: METRIC CARDS (Högst upp) ---
    st.subheader("💡 Dagens Guldkorn")
    col1, col2, col3 = st.columns(3)
    
    if all_corners:
        best_match = max(all_corners, key=lambda x: float(x['>9.5 (%)'].replace('%','')))
        col1.metric("Högst Sannolikhet (>9.5)", best_match['Match'], best_match['>9.5 (%)'])
        
        # Räknar ut ett snitt på alla matcher
        avg_exp = sum(d['Exp Tot'] for d in all_corners) / len(all_corners)
        col2.metric("Snitt Exp. Hörnor", f"{round(avg_exp, 1)} st")
        
        col3.metric("Antal spelbara val", len(top_picks))
    
    # --- IDÉ 1: FÄRGKODAD TABELL ---
    st.subheader("🎯 Detaljerad Analys")
    if all_corners:
        df = pd.DataFrame(all_corners)
        
        # Applicera färgkodning
        styled_df = df.style.applymap(color_value, subset=['>8.5 (%)', '>9.5 (%)'])
        
        # Visa tabellen
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.error("Kunde inte hitta data för lagen. Kontrollera stavningen!")

# Instruktion för att komma igång
else:
    st.info("Fyll i matcher i menyn till vänster. Om du vill se 'Value', fyll i det odds du hittar hos ditt spelbolag.")
