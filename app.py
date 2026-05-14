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
# CLEAN CSS
# =========================================================
st.markdown("""
<style>

.block-container {
    padding-top: 1.5rem;
    max-width: 1400px;
}

.market-title {
    font-size: 22px;
    font-weight: 700;
    margin-top: 20px;
    margin-bottom: 10px;
}

.sub-market {
    font-size: 17px;
    font-weight: 600;
    margin-top: 15px;
    margin-bottom: 8px;
}

.match-header {
    font-size: 28px;
    font-weight: 800;
}

.league-text {
    color: gray;
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# DATE / SEASON
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

    "England: Premier League":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/E0.csv",

    "England: Championship":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/E1.csv",

    "Spain: La Liga":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/SP1.csv",

    "Italy: Serie A":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/I1.csv",

    "Germany: Bundesliga":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/D1.csv",

    "France: Ligue 1":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/F1.csv",

    "Netherlands: Eredivisie":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/N1.csv",

    "Portugal: Liga Portugal":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/P1.csv",

    "Turkey: Super Lig":
        f"https://www.football-data.co.uk/mmz4281/{season_str}/T1.csv",

    "Sweden: Allsvenskan":
        "https://www.football-data.co.uk/new/SWE.csv",

    "Denmark: Superliga":
        "https://www.football-data.co.uk/new/DNK.csv"
}

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data(ttl=3600)
def get_league_stats(url):

    df = pd.read_csv(
        url,
        encoding="unicode_escape",
        on_bad_lines="skip"
    )

    # Specialhantering för Sverige/Danmark
    if 'SWE.csv' in url or 'DNK.csv' in url:

        df['parsed_date'] = pd.to_datetime(
            df['Date'],
            dayfirst=True,
            errors='coerce'
        )

        df = df[
            df['parsed_date'].dt.year ==
            datetime.datetime.now().year
        ]

    team_stats = {}

    for _, row in df.iterrows():

        h = (
            row.get("HomeTeam")
            if pd.notna(row.get("HomeTeam"))
            else row.get("Home")
        )

        a = (
            row.get("AwayTeam")
            if pd.notna(row.get("AwayTeam"))
            else row.get("Away")
        )

        if pd.isna(h) or pd.isna(a):
            continue

        h = str(h).strip()
        a = str(a).strip()

        for team in [h, a]:

            if team not in team_stats:

                team_stats[team] = {

                    "corners_for": [],
                    "corners_against": [],

                    "cards_for": [],
                    "cards_against": [],

                    "goals_for": [],
                    "goals_against": []
                }

        try:

            # CORNERS
            hc = float(row.get("HC", 0))
            ac = float(row.get("AC", 0))

            # CARDS
            hy = float(row.get("HY", 0))
            hr = float(row.get("HR", 0))

            ay = float(row.get("AY", 0))
            ar = float(row.get("AR", 0))

            # GOALS
            hg = float(row.get("FTHG", 0))
            ag = float(row.get("FTAG", 0))

            # HOME
            team_stats[h]["corners_for"].append(hc)
            team_stats[h]["corners_against"].append(ac)

            team_stats[h]["cards_for"].append(hy + hr)
            team_stats[h]["cards_against"].append(ay + ar)

            team_stats[h]["goals_for"].append(hg)
            team_stats[h]["goals_against"].append(ag)

            # AWAY
            team_stats[a]["corners_for"].append(ac)
            team_stats[a]["corners_against"].append(hc)

            team_stats[a]["cards_for"].append(ay + ar)
            team_stats[a]["cards_against"].append(hy + hr)

            team_stats[a]["goals_for"].append(ag)
            team_stats[a]["goals_against"].append(hg)

        except:
            continue

    final_stats = {}

    for team, d in team_stats.items():

        if len(d["corners_for"]) == 0:
            continue

        final_stats[team] = {

            "avg_corners_for":
                round(sum(d["corners_for"]) / len(d["corners_for"]), 2),

            "avg_corners_against":
                round(sum(d["corners_against"]) / len(d["corners_against"]), 2),

            "avg_cards_for":
                round(sum(d["cards_for"]) / len(d["cards_for"]), 2),

            "avg_cards_against":
                round(sum(d["cards_against"]) / len(d["cards_against"]), 2),

            "avg_goals_for":
                round(sum(d["goals_for"]) / len(d["goals_for"]), 2),

            "avg_goals_against":
                round(sum(d["goals_against"]) / len(d["goals_against"]), 2),
        }

    return final_stats

# =========================================================
# POISSON
# =========================================================
def poisson_probability(lam, k):

    return (lam ** k * math.exp(-lam)) / math.factorial(k)

def calculate_market(lam, line):

    prob_under = sum(
        poisson_probability(lam, k)
        for k in range(math.ceil(line))
    )

    prob = (1 - prob_under) * 100

    if prob <= 0:
        prob = 0.01

    odds = round(100 / prob, 2)

    return round(prob, 1), odds

# =========================================================
# MARKET TABLE
# =========================================================
def build_market_table(expected, lines):

    rows = []

    for line in lines:

        prob, odds = calculate_market(expected, line)

        rows.append({
            "Line": f"Over {line}",
            "Probability": f"{prob}%",
            "Odds": odds
        })

    return pd.DataFrame(rows)

# =========================================================
# SESSION STATE
# =========================================================
if "matches" not in st.session_state:
    st.session_state.matches = []

# =========================================================
# HEADER
# =========================================================
st.title("⚽ Master Football Predictor")

st.caption("Professional football analytics dashboard")

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:

    st.header("➕ Add Match")

    selected_league = st.selectbox(
        "League",
        list(LEAGUE_MAP.keys())
    )

    stats = get_league_stats(
        LEAGUE_MAP[selected_league]
    )

    teams = sorted(list(stats.keys()))

    home_team = st.selectbox(
        "Home Team",
        teams
    )

    away_team = st.selectbox(
        "Away Team",
        teams,
        index=1 if len(teams) > 1 else 0
    )

    if st.button(
        "Add Match",
        use_container_width=True
    ):

        st.session_state.matches.append({

            "league": selected_league,
            "home": home_team,
            "away": away_team
        })

# =========================================================
# NO MATCHES
# =========================================================
if len(st.session_state.matches) == 0:

    st.info("Add matches from the sidebar.")

# =========================================================
# MATCHES LOOP
# =========================================================
remove_idx = None

for idx, match in enumerate(st.session_state.matches):

    stats = get_league_stats(
        LEAGUE_MAP[match["league"]]
    )

    hs = stats[match["home"]]
    ast = stats[match["away"]]

    # =====================================================
    # EXPECTED VALUES
    # =====================================================

    # CORNERS
    exp_home_corners = (
        hs["avg_corners_for"] +
        ast["avg_corners_against"]
    ) / 2

    exp_away_corners = (
        ast["avg_corners_for"] +
        hs["avg_corners_against"]
    ) / 2

    exp_total_corners = (
        exp_home_corners +
        exp_away_corners
    )

    # CARDS
    exp_home_cards = (
        hs["avg_cards_for"] +
        ast["avg_cards_against"]
    ) / 2

    exp_away_cards = (
        ast["avg_cards_for"] +
        hs["avg_cards_against"]
    ) / 2

    exp_total_cards = (
        exp_home_cards +
        exp_away_cards
    )

    # GOALS
    exp_home_goals = (
        hs["avg_goals_for"] +
        ast["avg_goals_against"]
    ) / 2

    exp_away_goals = (
        ast["avg_goals_for"] +
        hs["avg_goals_against"]
    ) / 2

    exp_total_goals = (
        exp_home_goals +
        exp_away_goals
    )

    # =====================================================
    # EXPANDER
    # =====================================================
    with st.expander(
        f"{match['home']} vs {match['away']} | {match['league']}",
        expanded=True
    ):

        top1, top2 = st.columns([10,1])

        with top1:

            st.markdown(
                f'<div class="match-header">{match["home"]} vs {match["away"]}</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                f'<div class="league-text">{match["league"]}</div>',
                unsafe_allow_html=True
            )

        with top2:

            if st.button(
                "❌",
                key=f"remove_{idx}"
            ):
                remove_idx = idx

        st.divider()

        # =====================================================
        # CORNERS
        # =====================================================
        st.markdown(
            '<div class="market-title">🎯 Corners</div>',
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                '<div class="sub-market">TOTAL</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_total_corners,
                    [8.5, 9.5, 10.5, 11.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        with c2:

            st.markdown(
                f'<div class="sub-market">{match["home"].upper()}</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_home_corners,
                    [3.5, 4.5, 5.5, 6.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        with c3:

            st.markdown(
                f'<div class="sub-market">{match["away"].upper()}</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_away_corners,
                    [3.5, 4.5, 5.5, 6.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        st.divider()

        # =====================================================
        # CARDS
        # =====================================================
        st.markdown(
            '<div class="market-title">🟨 Cards</div>',
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                '<div class="sub-market">TOTAL</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_total_cards,
                    [3.5, 4.5, 5.5, 6.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        with c2:

            st.markdown(
                f'<div class="sub-market">{match["home"].upper()}</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_home_cards,
                    [0.5, 1.5, 2.5, 3.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        with c3:

            st.markdown(
                f'<div class="sub-market">{match["away"].upper()}</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_away_cards,
                    [0.5, 1.5, 2.5, 3.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        st.divider()

        # =====================================================
        # GOALS
        # =====================================================
        st.markdown(
            '<div class="market-title">⚽ Goals</div>',
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.markdown(
                '<div class="sub-market">TOTAL</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_total_goals,
                    [1.5, 2.5, 3.5, 4.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        with c2:

            st.markdown(
                f'<div class="sub-market">{match["home"].upper()}</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_home_goals,
                    [0.5, 1.5, 2.5, 3.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        with c3:

            st.markdown(
                f'<div class="sub-market">{match["away"].upper()}</div>',
                unsafe_allow_html=True
            )

            st.dataframe(
                build_market_table(
                    exp_away_goals,
                    [0.5, 1.5, 2.5, 3.5]
                ),
                hide_index=True,
                use_container_width=True
            )

        st.divider()

        # =====================================================
        # TEAM STATS
        # =====================================================
        st.markdown(
            '<div class="market-title">📊 Team Statistics</div>',
            unsafe_allow_html=True
        )

        stats_df = pd.DataFrame({

            "Stat": [

                "Corners For",
                "Corners Against",

                "Cards For",
                "Cards Against",

                "Goals For",
                "Goals Against"
            ],

            match["home"]: [

                hs["avg_corners_for"],
                hs["avg_corners_against"],

                hs["avg_cards_for"],
                hs["avg_cards_against"],

                hs["avg_goals_for"],
                hs["avg_goals_against"]
            ],

            match["away"]: [

                ast["avg_corners_for"],
                ast["avg_corners_against"],

                ast["avg_cards_for"],
                ast["avg_cards_against"],

                ast["avg_goals_for"],
                ast["avg_goals_against"]
            ]
        })

        st.dataframe(
            stats_df,
            hide_index=True,
            use_container_width=True
        )

# =========================================================
# REMOVE MATCH
# =========================================================
if remove_idx is not None:

    st.session_state.matches.pop(remove_idx)

    st.rerun()
