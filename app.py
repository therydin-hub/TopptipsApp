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

st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }

    div[data-testid="stExpander"] {
        background-color: white;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LIGAKONFIGURATION
# ==========================================
now = datetime.datetime.now()

# Skapar säsongsformatet (t.ex. 2526 för säsongen 2025/2026)
season_str = (
    f"{str(now.year-1)[-2:]}{str(now.year)[-2:]}"
    if now.month < 8
    else f"{str(now.year)[-2:]}{str(now.year+1)[-2:]}"
)

LEAGUE_MAP = {
    "England: Premier League": f"https://www.football-data.co.uk/mmz4281/{season_str}/E0.csv",
    "England: Championship": f"https://www.football-data.co.uk/mmz4281/{season_str}/E1.csv",
    "England: League 1": f"https://www.football-data.co.uk/mmz4281/{season_str}/E2.csv",
    "England: League 2": f"https://www.football-data.co.uk/mmz4281/{season_str}/E3.csv",
    "England: National League": f"https://www.football-data.co.uk/mmz4281/{season_str}/EC.csv",

    "Spanien: La Liga 1": f"https://www.football-data.co.uk/mmz4281/{season_str}/SP1.csv",
    "Spanien: La Liga 2": f"https://www.football-data.co.uk/mmz4281/{season_str}/SP2.csv",

    "Italien: Serie A": f"https://www.football-data.co.uk/mmz4281/{season_str}/I1.csv",
    "Italien: Serie B": f"https://www.football-data.co.uk/mmz4281/{season_str}/I2.csv",

    "Tyskland: Bundesliga 1": f"https://www.football-data.co.uk/mmz4281/{season_str}/D1.csv",
    "Tyskland: Bundesliga 2": f"https://www.football-data.co.uk/mmz4281/{season_str}/D2.csv",

    "Frankrike: Ligue 1": f"https://www.football-data.co.uk/mmz4281/{season_str}/F1.csv",
    "Frankrike: Ligue 2": f"https://www.football-data.co.uk/mmz4281/{season_str}/F2.csv",

    "Holland: Eredivisie": f"https://www.football-data.co.uk/mmz4281/{season_str}/N1.csv",

    "Belgien: Jupiler League": f"https://www.football-data.co.uk/mmz4281/{season_str}/B1.csv",

    "Portugal: Liga I": f"https://www.football-data.co.uk/mmz4281/{season_str}/P1.csv",

    "Turkiet: Süper Lig": f"https://www.football-data.co.uk/mmz4281/{season_str}/T1.csv",

    "Sverige: Allsvenskan": "https://www.football-data.co.uk/new/SWE.csv",

    "Danmark: Superliga": "https://www.football-data.co.uk/new/DNK.csv"
}

# ==========================================
# 3. LOGIK & BERÄKNINGAR
# ==========================================
@st.cache_data(ttl=3600)
def get_league_stats(url):

    try:
        df = pd.read_csv(
            url,
            encoding='unicode_escape',
            on_bad_lines='skip'
        )

        # Specialhantering för Sverige/Danmark
        if 'SWE.csv' in url or 'DNK.csv' in url:
            df['parsed_date'] = pd.to_datetime(
                df['Date'],
                dayfirst=True,
                errors='coerce'
            )

            df = df[df['parsed_date'].dt.year == datetime.datetime.now().year]

        team_stats = {}

        for _, row in df.iterrows():

            h_val = (
                row.get('Home')
                if pd.notna(row.get('Home'))
                else row.get('HomeTeam')
            )

            a_val = (
                row.get('Away')
                if pd.notna(row.get('Away'))
                else row.get('AwayTeam')
            )

            if pd.isna(h_val) or pd.isna(a_val):
                continue

            h = str(h_val).strip()
            a = str(a_val).strip()

            for team in [h, a]:
                if team not in team_stats:
                    team_stats[team] = {
                        'corners_for': [],
                        'corners_against': [],
                        'cards_for': [],
                        'cards_against': []
                    }

            try:
                hc = float(row.get('HC', 0))
                ac = float(row.get('AC', 0))

                hy = float(row.get('HY', 0))
                hr = float(row.get('HR', 0))

                ay = float(row.get('AY', 0))
                ar = float(row.get('AR', 0))

                # Hörnor
                team_stats[h]['corners_for'].append(hc)
                team_stats[h]['corners_against'].append(ac)

                team_stats[a]['corners_for'].append(ac)
                team_stats[a]['corners_against'].append(hc)

                # Kort
                team_stats[h]['cards_for'].append(hy + hr)
                team_stats[h]['cards_against'].append(ay + ar)

                team_stats[a]['cards_for'].append(ay + ar)
                team_stats[a]['cards_against'].append(hy + hr)

            except:
                continue

        final_stats = {}

        for team, data in team_stats.items():

            if len(data['corners_for']) == 0:
                continue

            final_stats[team] = {
                "avg_corners_for": round(
                    sum(data['corners_for']) / len(data['corners_for']), 2
                ),

                "avg_corners_against": round(
                    sum(data['corners_against']) / len(data['corners_against']), 2
                ),

                "avg_cards_for": round(
                    sum(data['cards_for']) / len(data['cards_for']), 2
                ),

                "avg_cards_against": round(
                    sum(data['cards_against']) / len(data['cards_against']), 2
                )
            }

        return final_stats

    except Exception as e:
        st.error(f"Fel vid hämtning av data: {e}")
        return {}


def poisson_probability(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)


def format_odds(lam, line):

    prob_under_or_equal = sum(
        poisson_probability(lam, k)
        for k in range(math.ceil(line))
    )

    prob = (1 - prob_under_or_equal) * 100

    if prob <= 0.5:
        return "0% (-)"

    odds = round(100 / prob, 2)

    return f"{round(prob,1)}% ({odds})"


# ==========================================
# 4. SIDOMENY
# ==========================================
with st.sidebar:

    st.header("⚙️ Matchval")

    league_name = st.selectbox(
        "1. Välj Liga:",
        list(LEAGUE_MAP.keys())
    )

    stats = get_league_stats(LEAGUE_MAP[league_name])

    team_list = sorted(list(stats.keys()))

    if team_list:

        h_team = st.selectbox(
            "2. Hemmalag:",
            team_list,
            index=0
        )

        a_team = st.selectbox(
            "3. Bortalag:",
            team_list,
            index=1 if len(team_list) > 1 else 0
        )

        calculate_btn = st.button(
            "Kör Analys 🚀",
            use_container_width=True
        )

    else:
        st.error("Kunde inte hämta lag för denna liga.")
        calculate_btn = False


# ==========================================
# 5. HUVUDTITEL
# ==========================================
st.title("⚽ Master Stats Predictor")

st.caption(
    f"Analyserar {league_name} baserat på aktuell säsongsdata."
)

# ==========================================
# 6. ANALYS
# ==========================================
if calculate_btn:

    try:

        hs = stats[h_team]
        ast = stats[a_team]

        # ======================================
        # HÖRNBERÄKNINGAR
        # ======================================
        exp_hc = (
            hs['avg_corners_for'] +
            ast['avg_corners_against']
        ) / 2

        exp_ac = (
            ast['avg_corners_for'] +
            hs['avg_corners_against']
        ) / 2

        exp_tot_c = exp_hc + exp_ac

        # ======================================
        # KORTBERÄKNINGAR
        # ======================================
        exp_h_card = (
            hs['avg_cards_for'] +
            ast['avg_cards_against']
        ) / 2

        exp_a_card = (
            ast['avg_cards_for'] +
            hs['avg_cards_against']
        ) / 2

        exp_tot_card = exp_h_card + exp_a_card

        # ======================================
        # TABS
        # ======================================
        tab1, tab2, tab3 = st.tabs([
            "🎯 HÖRN-ANALYS",
            "🟨 KORT-ANALYS",
            "📊 LAG-STATISTIK"
        ])

        # ======================================
        # HÖRNOR
        # ======================================
        with tab1:

            res_corners = [{
                'Match': f"{h_team} vs {a_team}",

                'Total Exp': round(exp_tot_c, 1),

                '>8.5': format_odds(exp_tot_c, 8.5),
                '>9.5': format_odds(exp_tot_c, 9.5),
                '>10.5': format_odds(exp_tot_c, 10.5),
                '>11.5': format_odds(exp_tot_c, 11.5),

                f'H ({h_team})': round(exp_hc, 1),

                '>H 3.5': format_odds(exp_hc, 3.5),
                '>H 4.5': format_odds(exp_hc, 4.5),
                '>H 5.5': format_odds(exp_hc, 5.5),

                f'B ({a_team})': round(exp_ac, 1),

                '>B 3.5': format_odds(exp_ac, 3.5),
                '>B 4.5': format_odds(exp_ac, 4.5),
                '>B 5.5': format_odds(exp_ac, 5.5)
            }]

            st.dataframe(
                pd.DataFrame(res_corners),
                use_container_width=True,
                hide_index=True
            )

        # ======================================
        # KORT
        # ======================================
        with tab2:

            res_cards = [{
                'Match': f"{h_team} vs {a_team}",

                'Total Exp': round(exp_tot_card, 1),

                '>3.5': format_odds(exp_tot_card, 3.5),
                '>4.5': format_odds(exp_tot_card, 4.5),
                '>5.5': format_odds(exp_tot_card, 5.5),
                '>6.5': format_odds(exp_tot_card, 6.5),

                f'H ({h_team})': round(exp_h_card, 1),

                '>H 0.5': format_odds(exp_h_card, 0.5),
                '>H 1.5': format_odds(exp_h_card, 1.5),
                '>H 2.5': format_odds(exp_h_card, 2.5),

                f'B ({a_team})': round(exp_a_card, 1),

                '>B 0.5': format_odds(exp_a_card, 0.5),
                '>B 1.5': format_odds(exp_a_card, 1.5),
                '>B 2.5': format_odds(exp_a_card, 2.5)
            }]

            st.dataframe(
                pd.DataFrame(res_cards),
                use_container_width=True,
                hide_index=True
            )

        # ======================================
        # LAGSTATISTIK
        # ======================================
        with tab3:

            stats_df = pd.DataFrame({
                "Statistik": [
                    "Snitt hörnor FOR",
                    "Snitt hörnor AGAINST",
                    "Snitt kort FOR",
                    "Snitt kort AGAINST"
                ],

                h_team: [
                    hs['avg_corners_for'],
                    hs['avg_corners_against'],
                    hs['avg_cards_for'],
                    hs['avg_cards_against']
                ],

                a_team: [
                    ast['avg_corners_for'],
                    ast['avg_corners_against'],
                    ast['avg_cards_for'],
                    ast['avg_cards_against']
                ]
            })

            st.dataframe(
                stats_df,
                use_container_width=True,
                hide_index=True
            )

    except Exception as e:

        st.error(
            f"Ett fel uppstod vid analysen: {e}"
        )

else:

    st.info(
        "Välj en liga och två lag i menyn till vänster för att starta analysen."
    )
