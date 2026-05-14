import streamlit as st
import pandas as pd
import datetime
import math

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Master Football Predictor",
    page_icon="⚽",
    layout="wide"
)

# =========================================================
# CUSTOM CSS
# =========================================================
st.markdown("""
<style>

.block-container {
    padding-top: 2rem;
}

.match-card {
    background-color: #ffffff;
    padding: 20px;
    border-radius: 14px;
    margin-bottom: 25px;
    border: 1px solid #e6e6e6;
}

.section-title {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 10px;
    margin-top: 15px;
}

.market-box {
    background: #f8f9fb;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 10px;
}

.market-line {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #ececec;
}

.market-line:last-child {
    border-bottom: none;
}

.big-title {
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 5px;
}

.sub-title {
    color: #777;
    margin-bottom: 25px;
}

hr {
    margin-top: 30px;
    margin-bottom: 30px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# SEASON STRING
# =========================================================
now = datetime.datetime.now()

season_str = (
    f"{str(now.year-1)[-2:]}{str(now.year)[-2:]}"
    if now.month < 8
    else f"{str(now.year)[-2:]}{str(now.year+1)[-2:]}"
)

# =========================================================
# LEAGUES
# =========================================================
LEAGUE_MAP = {
    "England: Premier League": f"https://www.football-data.co.uk/mmz4281/{season_str}/E0.csv",
    "England: Championship": f"https://www.football-data.co.uk/mmz4281/{season_str}/E1.csv",

    "Spain: La Liga": f"https://www.football-data.co.uk/mmz4281/{season_str}/SP1.csv",

    "Italy: Serie A": f"https://www.football-data.co.uk/mmz4281/{season_str}/I1.csv",

    "Germany: Bundesliga": f"https://www.football-data.co.uk/mmz4281/{season_str}/D1.csv",

    "France: Ligue 1": f"https://www.football-data.co.uk/mmz4281/{season_str}/F1.csv",

    "Netherlands: Eredivisie": f"https://www.football-data.co.uk/mmz4281/{season_str}/N1.csv",

    "Portugal: Liga Portugal": f"https://www.football-data.co.uk/mmz4281/{season_str}/P1.csv",

    "Turkey: Super Lig": f"https://www.football-data.co.uk/mmz4281/{season_str}/T1.csv",

    "Sweden: Allsvenskan": "https://www.football-data.co.uk/new/SWE.csv",

    "Denmark: Superliga": "https://www.football-data.co.uk/new/DNK.csv"
}

# =========================================================
# CACHE DATA
# =========================================================
@st.cache_data(ttl=3600)
def get_league_stats(url):

    df = pd.read_csv(
        url,
        encoding='unicode_escape',
        on_bad_lines='skip'
    )

    team_stats = {}

    for _, row in df.iterrows():

        h = row.get('HomeTeam')
        a = row.get('AwayTeam')

        if pd.isna(h) or pd.isna(a):
            continue

        h = str(h).strip()
        a = str(a).strip()

        for team in [h, a]:

            if team not in team_stats:

                team_stats[team] = {
                    'corners_for': [],
                    'corners_against': [],

                    'cards_for': [],
                    'cards_against': [],

                    'goals_for': [],
                    'goals_against': []
                }

        try:

            # CORNERS
            hc = float(row.get('HC', 0))
            ac = float(row.get('AC', 0))

            # CARDS
            hy = float(row.get('HY', 0))
            hr = float(row.get('HR', 0))

            ay = float(row.get('AY', 0))
            ar = float(row.get('AR', 0))

            # GOALS
            hg = float(row.get('FTHG', 0))
            ag = float(row.get('FTAG', 0))

            # HOME
            team_stats[h]['corners_for'].append(hc)
            team_stats[h]['corners_against'].append(ac)

            team_stats[h]['cards_for'].append(hy + hr)
            team_stats[h]['cards_against'].append(ay + ar)

            team_stats[h]['goals_for'].append(hg)
            team_stats[h]['goals_against'].append(ag)

            # AWAY
            team_stats[a]['corners_for'].append(ac)
            team_stats[a]['corners_against'].append(hc)

            team_stats[a]['cards_for'].append(ay + ar)
            team_stats[a]['cards_against'].append(hy + hr)

            team_stats[a]['goals_for'].append(ag)
            team_stats[a]['goals_against'].append(hg)

        except:
            continue

    final_stats = {}

    for team, d in team_stats.items():

        if len(d['corners_for']) == 0:
            continue

        final_stats[team] = {

            "avg_corners_for": round(sum(d['corners_for']) / len(d['corners_for']), 2),
            "avg_corners_against": round(sum(d['corners_against']) / len(d['corners_against']), 2),

            "avg_cards_for": round(sum(d['cards_for']) / len(d['cards_for']), 2),
            "avg_cards_against": round(sum(d['cards_against']) / len(d['cards_against']), 2),

            "avg_goals_for": round(sum(d['goals_for']) / len(d['goals_for']), 2),
            "avg_goals_against": round(sum(d['goals_against']) / len(d['goals_against']), 2),
        }

    return final_stats

# =========================================================
# POISSON
# =========================================================
def poisson_probability(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def calc_over_probability(lam, line):

    prob_under_or_equal = sum(
        poisson_probability(lam, k)
        for k in range(math.ceil(line))
    )

    prob = (1 - prob_under_or_equal) * 100

    if prob <= 0:
        return "0%"

    odds = round(100 / prob, 2)

    return f"{round(prob,1)}%  |  Odds {odds}"

# =========================================================
# SESSION STATE
# =========================================================
if "matches" not in st.session_state:
    st.session_state.matches = []

# =========================================================
# HEADER
# =========================================================
st.markdown('<div class="big-title">⚽ Master Football Predictor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Professional betting analytics dashboard</div>', unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:

    st.header("➕ Add Match")

    league = st.selectbox(
        "League",
        list(LEAGUE_MAP.keys())
    )

    stats = get_league_stats(LEAGUE_MAP[league])

    teams = sorted(list(stats.keys()))

    home_team = st.selectbox(
        "Home Team",
        teams,
        key="home"
    )

    away_team = st.selectbox(
        "Away Team",
        teams,
        index=1 if len(teams) > 1 else 0,
        key="away"
    )

    if st.button("Add Match", use_container_width=True):

        st.session_state.matches.append({
            "league": league,
            "home": home_team,
            "away": away_team
        })

# =========================================================
# MARKET RENDER
# =========================================================
def render_market(title, expected, lines):

    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="market-box"><b>Expected:</b> {round(expected,2)}</div>',
        unsafe_allow_html=True
    )

    for line in lines:

        result = calc_over_probability(expected, line)

        st.markdown(f"""
        <div class="market-line">
            <div>Over {line}</div>
            <div>{result}</div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# DISPLAY MATCHES
# =========================================================
if len(st.session_state.matches) == 0:

    st.info("Add matches from the sidebar to begin.")

else:

    remove_index = None

    for idx, match in enumerate(st.session_state.matches):

        stats = get_league_stats(LEAGUE_MAP[match['league']])

        hs = stats[match['home']]
        ast = stats[match['away']]

        # =================================================
        # EXPECTED VALUES
        # =================================================

        # CORNERS
        exp_hc = (hs['avg_corners_for'] + ast['avg_corners_against']) / 2
        exp_ac = (ast['avg_corners_for'] + hs['avg_corners_against']) / 2
        exp_total_corners = exp_hc + exp_ac

        # CARDS
        exp_hcards = (hs['avg_cards_for'] + ast['avg_cards_against']) / 2
        exp_acards = (ast['avg_cards_for'] + hs['avg_cards_against']) / 2
        exp_total_cards = exp_hcards + exp_acards

        # GOALS
        exp_hgoals = (hs['avg_goals_for'] + ast['avg_goals_against']) / 2
        exp_agoals = (ast['avg_goals_for'] + hs['avg_goals_against']) / 2
        exp_total_goals = exp_hgoals + exp_agoals

        # =================================================
        # MATCH CARD
        # =================================================
        with st.container():

            st.markdown('<div class="match-card">', unsafe_allow_html=True)

            col1, col2 = st.columns([8,1])

            with col1:

                st.markdown(f"""
                ### {match['home']} vs {match['away']}
                **{match['league']}**
                """)

            with col2:

                if st.button("❌", key=f"remove_{idx}"):

                    remove_index = idx

            st.divider()

            # =================================================
            # MARKETS
            # =================================================
            c1, c2, c3 = st.columns(3)

            # CORNERS
            with c1:

                render_market(
                    "🎯 Corners",
                    exp_total_corners,
                    [8.5, 9.5, 10.5, 11.5]
                )

            # CARDS
            with c2:

                render_market(
                    "🟨 Cards",
                    exp_total_cards,
                    [3.5, 4.5, 5.5, 6.5]
                )

            # GOALS
            with c3:

                render_market(
                    "⚽ Goals",
                    exp_total_goals,
                    [1.5, 2.5, 3.5, 4.5]
                )

            st.divider()

            # =================================================
            # TEAM STATS
            # =================================================
            st.markdown("### 📊 Team Statistics")

            stats_df = pd.DataFrame({

                "Stat": [
                    "Corners For",
                    "Corners Against",

                    "Cards For",
                    "Cards Against",

                    "Goals For",
                    "Goals Against"
                ],

                match['home']: [

                    hs['avg_corners_for'],
                    hs['avg_corners_against'],

                    hs['avg_cards_for'],
                    hs['avg_cards_against'],

                    hs['avg_goals_for'],
                    hs['avg_goals_against']
                ],

                match['away']: [

                    ast['avg_corners_for'],
                    ast['avg_corners_against'],

                    ast['avg_cards_for'],
                    ast['avg_cards_against'],

                    ast['avg_goals_for'],
                    ast['avg_goals_against']
                ]
            })

            st.dataframe(
                stats_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown('</div>', unsafe_allow_html=True)

    # REMOVE MATCH
    if remove_index is not None:

        st.session_state.matches.pop(remove_index)
        st.rerun()
