import os
import json
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(page_title="SCANNER ⚽⚽", page_icon="⚽", layout="wide")

# ---------------------------------------------------------
# CONSTANTS & PROFILE DEFINITIONS
# ---------------------------------------------------------
PROFILE_NAMES = {
    1: "Profile 1: The Unlucky Dominator",
    2: "Profile 2: The Fraudulent Winner",
    3: "Profile 3: The Genuine Elite",
    4: "Profile 4: The Structural Crisis",
    5: "Profile 5: Neutral / Unclassified"
}

MATCHUP_MATRIX = {
    (1, 2): {
        "dynamic": "Bookies price recent points, undervaluing Home Team and overvaluing Away Team.",
        "selection": "Asian Handicap / Moneyline on Home Team"
    },
    (1, 4): {
        "dynamic": "Home Team dominates play but wastes chances; Away Team leaks chances and cannot score.",
        "selection": "Home Team Win & Under 3.5 Goals OR Home Team -1 Asian Handicap"
    },
    (1, 1): {
        "dynamic": "Both teams create high xG overall, but both defenses are strong and both front lines are cold.",
        "selection": "Under 2.5 Goals OR Both Teams to Score - NO"
    },
    (1, 3): {
        "dynamic": "Both teams control games, but Away Team actually converts while Home Team wastes chances against a top-tier defense.",
        "selection": "Away Team Win (Moneyline) OR Away Team Draw No Bet"
    },
    (2, 2): {
        "dynamic": "Both teams rely on unsustainable luck while bleeding chances defensively. High chaos factor once luck runs out.",
        "selection": "Over 2.5 Goals OR Both Teams To Score"
    },
    (2, 4): {
        "dynamic": "Both allow high chance volume, but Home Team has clinical individuals while Away Team is completely broken.",
        "selection": "Over 2.5 Goals OR Both Teams To Score"
    },
    (3, 3): {
        "dynamic": "High-level tactical battle between two sharp teams. Tight margins make match-winner bets risky.",
        "selection": "Under 2.5 Goals OR Fade / Draw (Value Bet)"
    },
    (3, 4): {
        "dynamic": "Complete mismatch in quality, structure, and execution. High blowout potential.",
        "selection": "Home Team -1.5 Asian Handicap OR Home Team Win to Nil"
    },
    (4, 4): {
        "dynamic": "Both teams are defensively disorganized, wasteful, and error-prone. Total unpredictability.",
        "selection": "Over 2.5 Goals / BTTS OR Fade the Match Entirely"
    }
}

# ---------------------------------------------------------
# CORE ANALYTICAL FUNCTIONS
# ---------------------------------------------------------
def classify_profile(perf_potential: float, finishing_eff: float) -> int:
    """
    Classifies a team into one of the 5 profile types based on strict thresholds:
    - Profile 1: (xG - xGA > 1.00) AND (GS - xG < -0.50)
    - Profile 2: (xG - xGA < -1.00) AND (GS - xG > 0.50)
    - Profile 3: (xG - xGA > 1.00) AND (GS - xG > 0.50)
    - Profile 4: (xG - xGA < -1.00) AND (GS - xG < -0.50)
    - Profile 5: Neutral / Unclassified
    """
    if perf_potential > 1.00 and finishing_eff < -0.50:
        return 1
    elif perf_potential < -1.00 and finishing_eff > 0.50:
        return 2
    elif perf_potential > 1.00 and finishing_eff > 0.50:
        return 3
    elif perf_potential < -1.00 and finishing_eff < -0.50:
        return 4
    else:
        return 5

def extract_match_data(images, team_name, api_key):
    """
    Sends uploaded screenshots to Gemini 2.5 Flash via vision API 
    to extract structured match stats (Date, Opponent, Score, xG, xGA).
    """
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an automated vision processor extracting match card stats for {team_name}.
    Scan all provided images and return a JSON array containing objects for each match screenshot:
    [
      {{
        "date": "YYYY-MM-DD",
        "opponent": "Opponent Name",
        "gs": 0,
        "ga": 0,
        "xg": 0.00,
        "xga": 0.00,
        "xg_available": true
      }}
    ]
    If xG stats are unreadable or missing, set "xg_available": false and default xg/xga to 0.0.
    Output ONLY raw valid JSON.
    """
    
    contents = [prompt] + images
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    
    return json.loads(response.text)

# ---------------------------------------------------------
# USER INTERFACE LAYOUT
# ---------------------------------------------------------
st.title("SCANNER ⚽⚽")
st.caption("Quantitative Football Analyst & Vision Processor")

# Reset Functionality
if st.sidebar.button("Reset / New Analysis"):
    st.session_state.clear()
    st.rerun()

api_key = st.sidebar.text_input("Gemini API Key", type="password")

col1, col2 = st.columns(2)
with col1:
    home_team = st.text_input("Home Team Name")
    home_files = st.file_uploader("Upload Home Screenshots (5)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

with col2:
    away_team = st.text_input("Away Team Name")
    away_files = st.file_uploader("Upload Away Screenshots (5)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if st.button("Run SCANNER Analysis"):
    if not api_key:
        st.error("Please provide your Gemini API Key in the sidebar.")
    elif not home_team or not away_team:
        st.error("Please enter both team names.")
    elif len(home_files) == 0 or len(away_files) == 0:
        st.error("Please upload screenshots for both teams.")
    else:
        with st.spinner("Processing vision data and calculating matrix..."):
            home_images = [Image.open(f) for f in home_files]
            away_images = [Image.open(f) for f in away_files]
            
            home_data = extract_match_data(home_images, home_team, api_key)
            away_data = extract_match_data(away_images, away_team, api_key)
            
            # Calculations for Home Team
            sum_gs_h = sum(m["gs"] for m in home_data)
            sum_ga_h = sum(m["ga"] for m in home_data)
            sum_xg_h = sum(m["xg"] for m in home_data if m["xg_available"])
            sum_xga_h = sum(m["xga"] for m in home_data if m["xg_available"])
            fin_eff_h = sum_gs_h - sum_xg_h
            perf_pot_h = sum_xg_h - sum_xga_h
            profile_h = classify_profile(perf_pot_h, fin_eff_h)
            
            # Calculations for Away Team
            sum_gs_a = sum(m["gs"] for m in away_data)
            sum_ga_a = sum(m["ga"] for m in away_data)
            sum_xg_a = sum(m["xg"] for m in away_data if m["xg_available"])
            sum_xga_a = sum(m["xga"] for m in away_data if m["xg_available"])
            fin_eff_a = sum_gs_a - sum_xg_a
            perf_pot_a = sum_xg_a - sum_xga_a
            profile_a = classify_profile(perf_pot_a, fin_eff_a)
            
            # Matrix Lookup
            matchup_key = (profile_h, profile_a)
            inverted_key = (profile_a, profile_h)
            
            if matchup_key in MATCHUP_MATRIX:
                matchup_info = MATCHUP_MATRIX[matchup_key]
            elif inverted_key in MATCHUP_MATRIX:
                matchup_info = MATCHUP_MATRIX[inverted_key]
            else:
                matchup_info = {
                    "dynamic": "Neutral profile detected. Mid-tier statistical noise.",
                    "selection": "No clear statistical edge based on strict thresholds."
                }
            
            # Formatted Report Output
            st.text("================================================================================")
            st.markdown(f"### MATCH RESEARCH REPORT: {home_team.upper()} vs. {away_team.upper()}")
            st.markdown("Data Source: Uploaded Vision Data (Last 5 Domestic League Matches)")
            st.text("================================================================================")
            
            st.markdown(f"#### {home_team} Last 5 League Matches")
            for idx, m in enumerate(home_data, 1):
                xg_str = f"{m['xg']:.2f}" if m['xg_available'] else "[xG STATS NOT AVAILABLE]"
                xga_str = f"{m['xga']:.2f}" if m['xg_available'] else "[xG STATS NOT AVAILABLE]"
                st.write(f"{idx}. Date: {m['date']} | vs {m['opponent']} | Score: {m['gs']}-{m['ga']} | xG: {xg_str} | xGA: {xga_str}")
            
            st.markdown(f"""
            * **Sum Goals Scored (GS):** {sum_gs_h}
            * **Sum Goals Conceded (GA):** {sum_ga_h}
            * **Sum Expected Goals (xG):** {sum_xg_h:.2f}
            * **Sum Expected Goals Against (xGA):** {sum_xga_h:.2f}
            * **Finishing Efficiency (Sum GS - Sum xG):** {fin_eff_h:.2f}
            * **Performance Potential (Sum xG - Sum xGA):** {perf_pot_h:.2f}
            * **Assigned Profile:** {PROFILE_NAMES[profile_h]}
            """)
            
            st.markdown("---")
            st.markdown(f"#### {away_team} Last 5 League Matches")
            for idx, m in enumerate(away_data, 1):
                xg_str = f"{m['xg']:.2f}" if m['xg_available'] else "[xG STATS NOT AVAILABLE]"
                xga_str = f"{m['xga']:.2f}" if m['xg_available'] else "[xG STATS NOT AVAILABLE]"
                st.write(f"{idx}. Date: {m['date']} | vs {m['opponent']} | Score: {m['gs']}-{m['ga']} | xG: {xg_str} | xGA: {xga_str}")
            
            st.markdown(f"""
            * **Sum Goals Scored (GS):** {sum_gs_a}
            * **Sum Goals Conceded (GA):** {sum_ga_a}
            * **Sum Expected Goals (xG):** {sum_xg_a:.2f}
            * **Sum Expected Goals Against (xGA):** {sum_xga_a:.2f}
            * **Finishing Efficiency (Sum GS - Sum xG):** {fin_eff_a:.2f}
            * **Performance Potential (Sum xG - Sum xGA):** {perf_pot_a:.2f}
            * **Assigned Profile:** {PROFILE_NAMES[profile_a]}
            """)
            
            st.markdown("---")
            st.markdown("### 2. QUALITATIVE SYNTHESIS & MATCHUP ANALYSIS")
            st.markdown(f"- **Profile Matchup Dynamic:** {PROFILE_NAMES[profile_h]} vs. {PROFILE_NAMES[profile_a]}")
            st.markdown(f"- **Market Reality vs. Perception:** {matchup_info['dynamic']}")
            
            st.markdown("---")
            st.markdown("### 3. VALUE SELECTION RECOMMENDATION")
            st.markdown(f"- **Primary Selection:** {matchup_info['selection']}")
            st.markdown(f"- **Analytical Justification:** {home_team} Performance Potential is {perf_pot_h:.2f} (Finishing Efficiency: {fin_eff_h:.2f}). {away_team} Performance Potential is {perf_pot_a:.2f} (Finishing Efficiency: {fin_eff_a:.2f}).")
