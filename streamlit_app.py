import streamlit as st
from main import get_current_players  # change 'your_module' to the actual module name

# Title
st.title("Lista de Jugadores Actualizada")

# Load players
with st.spinner("Cargando jugadores..."):
    current_players = get_current_players(
        no_form=False,
        no_fixtures=False,
        no_home_boost=False,
        no_team_history_boost=False,
        alt_fixture_method=False,
        alt_positions=True,
        alt_prices=True,
        alt_price_trends=True,
        alt_forms=True,
        add_start_probability=True,
        no_penalty_takers_boost=False,
        nerf_penalty_boost=False,
        no_penalty_savers_boost=False,
        no_team_status_nerf=False,
        no_manual_boost=True,
        use_old_players_data=False,
        use_old_teams_data=False,
        use_comunio_price=False,
        biwenger_file_name="biwenger_laliga_data",
        elo_ratings_file_name="elo_ratings_laliga_data",
        ratings_file_name="sofascore_laliga_players_ratings",
        penalty_takers_file_name="transfermarket_laliga_penalty_takers",
        penalty_saves_file_name="transfermarket_laliga_penalty_savers",
        team_history_file_name="transfermarket_laliga_team_history",
        alt_positions_file_names=[
            "analiticafantasy_laliga_players_positions",
            "futbolfantasy_laliga_players_positions",
            "jornadaperfecta_laliga_players_positions",
        ],
        alt_prices_file_names=[
            "analiticafantasy_laliga_players_prices",
            "futbolfantasy_laliga_players_prices",
            "jornadaperfecta_laliga_players_prices",
        ],
        alt_price_trends_file_names=[
            "analiticafantasy_laliga_players_price_trends",
            "futbolfantasy_laliga_players_price_trends",
            "jornadaperfecta_laliga_players_price_trends",
        ],
        alt_forms_file_names=[
            "analiticafantasy_laliga_players_forms",
            "futbolfantasy_laliga_players_forms",
            "jornadaperfecta_laliga_players_forms",
        ],
        start_probability_file_names=[
            "analiticafantasy_laliga_players_start_probabilities",
            "futbolfantasy_laliga_players_start_probabilities",
            "jornadaperfecta_laliga_players_start_probabilities",
        ],
        is_country=False,
        extra_teams=False,
        debug=False,
    )
    current_players = sorted(
        current_players,
        key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
        reverse=False
    )

# Display players
st.subheader(f"{len(current_players)} jugadores encontrados")

for player in current_players:
    st.text(str(player))  # uses your __str__ or __repr__
