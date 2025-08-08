import os
import copy
from io import BytesIO

import requests
from PIL import Image
from unidecode import unidecode
import streamlit as st
from collections import Counter

from group_knapsack import print_best_full_teams, best_full_teams
from main import get_current_players, purge_everything
from useful_functions import read_dict_data

# Dummy lines to force Streamlit to track the json_files and csv_files directories
_ = os.listdir("json_files")
_ = os.listdir("csv_files")


st.set_page_config(
    page_title="Calculadora Fantasy",      # Título de la pestaña del navegador
    page_icon="logo.png",                  # Ruta relativa a tu imagen
    layout="centered",                     # 'wide' o 'centered'
    initial_sidebar_state="expanded"       # 'expanded', 'collapsed', o 'auto'
)

st.markdown(
    """
    <style>
        div[data-testid="stConnectionStatus"] {
           display: none !important;
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="
        position: sticky;
        top: 35px;
        width: 100%;
        z-index: 1000;
        text-align: right;
        padding-right: 50px;
        background: transparent;
    ">
        <img src="https://www.calculadorafantasy.com/logo.png" style="height:40px;">
    </div>
    """,
    unsafe_allow_html=True
)

def sort_players(players, sort_option):
    if sort_option == "Rentabilidad":
        min_price = min((p.price for p in players if p.price > 0), default=1)
        return sorted(
            players,
            key=lambda x: (x.value - 7) / max(x.price, min_price),
            reverse=True
        )
    elif sort_option == "Precio":
        return sorted(
            players,
            key=lambda x: (-x.price, -x.value, -x.form, -x.fixture, x.team)
        )
    elif sort_option == "Forma":
        return sorted(
            players,
            key=lambda x: (-x.form, -x.value, -x.fixture, x.price, x.team)
        )
    elif sort_option == "Partido":
        return sorted(
            players,
            key=lambda x: (-x.fixture, -x.value, -x.form, x.price, x.team)
        )
    elif sort_option == "Probabilidad":
        return sorted(
            players,
            key=lambda x: (-x.start_probability, -x.value, -x.form, -x.fixture, x.price, x.team)
        )
    elif sort_option == "Posición":
        position_priority = {"GK": 0, "DEF": 1, "MID": 2, "ATT": 3}
        return sorted(
            players,
            key=lambda x: (position_priority.get(x.position, 99), -x.value, -x.form, -x.fixture, x.price, x.team)
        )
    else:  # Puntuación
        return sorted(
            players,
            key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team)
        )

def display_valid_formations(formation_score_players_by_score, current_players, blinded_players_names=None):
    current_players_copy = copy.deepcopy(current_players)
    if blinded_players_names is None:
        blinded_players_names = set()
    blinded_players = [cp for cp in current_players_copy if cp.name in blinded_players_names]
    blinded_lines = {"ATT": [], "MID": [], "DEF": [], "GK": []}
    for blinded_player in blinded_players:
        blinded_lines[blinded_player.position].append(blinded_player)

    valid_formations = [
        (formation, round(score, 3), players)
        for formation, score, players in formation_score_players_by_score
        if score != -1
    ]

    show_formations = []
    for formation, score, players in valid_formations:
        actual_players = [
            next(cp for cp in current_players_copy if cp.name == p.name and cp.team == p.team)
            for p in players
        ]
        names_result_players = {player.name for player in actual_players}
        actual_formation = formation.copy()
        actual_score = sum(player.value for player in current_players_copy if player.name in names_result_players)
        # total_price = sum(player.price for player in players)
        actual_price = sum(player.price for player in current_players_copy if player.name in names_result_players)
        show_price = actual_price / 10 if is_biwenger else actual_price

        show_formations.append((actual_formation, actual_score, actual_players, show_price))

    for formation, score, players, price in show_formations:
        lines = {"ATT": [], "MID": [], "DEF": [], "GK": []}
        for player in players:
            lines[player.position].append(player)

        player_names = {p.name for p in players}
        missing_blinded = blinded_players_names - player_names
        missing_ordered = [cp for cp in current_players_copy if cp.name in missing_blinded]

        st.markdown(f"### Formación {formation}: {score:.3f} puntos – 💰 {price}M")
        if missing_ordered:
            # st.warning(f"No se pudo incluir a: {', '.join(missing_ordered)} con el presupuesto dado")
            for missing_player in missing_ordered:
                motivo = ""
                if len(blinded_lines[missing_player.position]) > len(lines[missing_player.position]):
                    motivo = " porque los otros jugadores blindados en esa posición son mejores"
                else:
                    motivo = " con el presupuesto dado"
                st.warning(f"No se pudo incluir a: **{missing_player.name}**{motivo}")

        for position in ["ATT", "MID", "DEF", "GK"]:
            if lines[position]:
                cols = st.columns(len(lines[position]), gap="small")
                for i, player in enumerate(lines[position]):
                    is_blinded = player.name in blinded_players_names
                    player_display = f"{player.name} ({player.start_probability * 100:.0f}%)"
                    player_display = f"🔒 {player_display}" if is_blinded else f"{player_display}"
                    # border_style = "2px solid #1f77b4" if is_blinded else "none"

                    with cols[i]:
                                # <div style='text-align:center; border:{border_style}; border-radius:10px; padding:5px;'>
                        st.markdown(
                            f"""
                                <div style='text-align:center'>
                                    <img src='{player.img_link}' height='70'><br>
                                    {player_display}
                                </div>
                                """,
                            unsafe_allow_html=True
                        )

        with st.expander("Ver todos los jugadores utilizados"):
            players_show = copy.deepcopy(players)
            for player in players_show:
                blinded_mark = "🔒 " if player.name in blinded_players_names else ""
                # st.markdown(f"- {player} {blinded_mark}")
                player.name = blinded_mark + player.name
                # player.name = player.name + blinded_mark
                print_player(player, small_size=1)

        st.markdown("---")

# Función para normalizar nombres
def normalize_name(name):
    # return unidecode(name).strip()
    # Paso 1: Proteger las ñ y Ñ temporalmente
    name = name.replace("ñ", "___ENYE___").replace("Ñ", "___ENYE_UPPER___")
    # Paso 2: Aplicar unidecode para quitar tildes y otros caracteres especiales
    normalized = unidecode(name)
    # Paso 3: Restaurar ñ y Ñ
    normalized = normalized.replace("___ENYE___", "ñ").replace("___ENYE_UPPER___", "Ñ")
    return normalized.strip()

def print_player(player, small_size=0):
    if small_size==0:
        player_cols = st.columns([12, 1.8, 1, 2, 1, 3])  # Adjust width ratio if needed
        player_cols[0].markdown(
            f"- **{player.name}** ({player.position}, {player.team}): {player.price}M - **{player.value:.3f} pts**"
        )
        player_cols[1].caption("Forma:")
        player_cols[2].image(player.form_arrow, output_format="PNG", width=24) #, use_container_width=True)
        player_cols[3].caption("Partido:")
        player_cols[4].image(player.fixture_arrow, output_format="PNG", width=24) #, use_container_width=True)
        player_cols[5].markdown(f"Titular: **{player.start_probability*100:.0f} %**")
    elif small_size==1:
        player_cols = st.columns([12, 2.7, 1.5, 3, 1.5, 5])  # Adjust width ratio if needed
        player_cols[0].markdown(
            f"""
                - **{player.name}** ({player.position}, {player.team}):  
                {player.price}M - **{player.value:.3f} pts**
            """
        )
        player_cols[1].markdown("")
        player_cols[1].caption("Forma:")
        player_cols[2].markdown("")
        player_cols[2].image(player.form_arrow, output_format="PNG", width=24)
        player_cols[3].markdown("")
        player_cols[3].caption("Partido:")
        player_cols[4].markdown("")
        player_cols[4].image(player.fixture_arrow, output_format="PNG", width=24)
        player_cols[5].markdown("")
        player_cols[5].markdown(f"Titular: **{player.start_probability*100:.0f} %**")
    elif small_size==2:
        player_cols = st.columns([5, 12, 5, 5, 5])  # Adjust width ratio if needed
        # player_cols[0].image(player.img_link, width=70)
        player_cols[0].markdown(
            f"<img src='{player.img_link}' height='{70}' style='object-fit: contain;'>",
            unsafe_allow_html=True
        )
        player_cols[1].markdown("")
        player_cols[1].markdown(
            f"""
                **{player.name}** ({player.position}, {player.team}):  
                {player.price}M - **{player.value:.3f} pts**
            """
        )
        player_cols[2].image(player.form_arrow, output_format="PNG", width=30)#, caption="Forma", use_container_width=True)
        player_cols[2].caption("Forma")
        player_cols[3].image(player.fixture_arrow, output_format="PNG", width=30)#, caption="Partido", use_container_width=True)
        player_cols[3].caption("Partido")
        player_cols[4].markdown(
            f"""
                Titular:  
                **{player.start_probability*100:.0f} %**
            """
        )
    elif small_size==3:
        player_cols = st.columns([7, 15, 5, 5])  # Adjust width ratio if needed
        # player_cols[0].image(player.img_link, width=70)
        player_cols[0].markdown(
            f"<img src='{player.img_link}' height='{70}' style='object-fit: contain;'>",
            unsafe_allow_html=True
        )
        player_cols[0].markdown(f"Titular: **{player.start_probability*100:.0f} %**")
        player_cols[1].markdown("")
        player_cols[1].markdown(
            f"""
                **{player.name}** ({player.position}, {player.team}):  
                {player.price}M - **{player.value:.3f} pts**
            """
        )
        player_cols[2].image(player.form_arrow, output_format="PNG", width=30)#, caption="Forma", use_container_width=True)
        player_cols[2].caption("Forma")
        player_cols[3].image(player.fixture_arrow, output_format="PNG", width=30)#, caption="Partido", use_container_width=True)
        player_cols[3].caption("Partido")
    else:
        player_cols = st.columns([12, 1.8, 1, 2, 1, 3])  # Adjust width ratio if needed
        player_cols[0].markdown(
            f"- **{player.name}** ({player.position}, {player.team}): {player.price}M - **{player.value:.3f} pts**"
        )
        player_cols[1].markdown("Forma:")
        player_cols[2].image(player.form_arrow, output_format="PNG") #, use_container_width=True)
        player_cols[3].markdown("Partido:")
        player_cols[4].image(player.fixture_arrow, output_format="PNG") #, use_container_width=True)
        player_cols[5].markdown(f"Titular: **{player.start_probability*100:.0f} %**")


st.title("Calculadora Fantasy 🤖")

st.markdown("---")

tab_labels = [
    "💰 Mejores 11s con presupuesto",
    "⚽ Mi mejor 11 posible",
    "📋 Lista de jugadores",
    "📈 Analizar mi mercado"
]
tabs = st.tabs(tab_labels)
# # Selector de funcionalidad principal
# st.markdown("# Selecciona funcionalidad")
# main_option = st.selectbox(
#     label=" ",
#     options=[
#         # "Lista de jugadores",
#         # "Mi mejor 11 posible",
#         # "Mejores 11s con presupuesto",
#         "📋 Lista de jugadores",
#         "⚽ Mi mejor 11 posible",
#         "💰 Mejores 11s con presupuesto",
#     ],
#     index=0
# )

# Sidebar filters
st.sidebar.header("Opciones")
app_option = st.sidebar.selectbox("Aplicación", ["LaLiga Fantasy", "Biwenger"], index=1)
penalties_option = st.sidebar.radio("¿Te importan los penaltis?", ["Sí", "No"], index=0)
sort_option = st.sidebar.selectbox("Ordenar por", ["Puntuación", "Rentabilidad", "Precio", "Forma", "Partido", "Probabilidad", "Posición"], index=0)

# Jornada
jornadas_dict = read_dict_data("forced_matches_laliga_2025_26")
display_to_key = {key.replace("_", " ").strip().title(): key for key in jornadas_dict}
display_options = ["Siguiente partido"] + list(display_to_key.keys())
selected_display_jornada = st.sidebar.selectbox("Jornada", options=display_options, format_func=lambda x: normalize_name(x), index=0)
selected_jornada = [] if selected_display_jornada == "Siguiente partido" else jornadas_dict[display_to_key[selected_display_jornada]]
jornadas_map = {
    "Una jornada (solo la jornada elegida)": 1,
    "Dos jornadas (jornada elegida +1)": 2,
    "Tres jornadas (jornada elegida +2)": 3,
}
disable_multi_jornada = selected_display_jornada == "Siguiente partido"
selected_num_jornadas_label = st.sidebar.selectbox(
    "Cuántas jornadas tener en cuenta",
    options=list(jornadas_map.keys()),
    format_func=lambda x: normalize_name(x),
    index=0,
    disabled=disable_multi_jornada
)
selected_num_jornadas = jornadas_map[selected_num_jornadas_label]
if disable_multi_jornada:
    st.sidebar.markdown("<span style='color:gray'>Selecciona una jornada específica para usar varias jornadas.</span>", unsafe_allow_html=True)

form_option = st.sidebar.radio("¿Ignorar estado de forma?", ["Sí", "No"], index=1)

is_biwenger = app_option == "Biwenger"
ignore_penalties = penalties_option == "No"
ignore_form = form_option == "Sí"

with st.spinner("Cargando jugadores..."):
    current_players = get_current_players(
        no_form=ignore_form,
        no_fixtures=False,
        no_home_boost=False,
        no_team_history_boost=False,
        alt_fixture_method=False,
        skip_arrows=False,
        use_laligafantasy_data=not is_biwenger,
        # alt_positions=not is_biwenger,
        # alt_prices=not is_biwenger,
        # alt_price_trends=not is_biwenger,
        # alt_forms=not is_biwenger,
        add_start_probability=True,
        no_penalty_takers_boost=False,
        nerf_penalty_boost=ignore_penalties,
        no_penalty_savers_boost=False,
        no_team_status_nerf=False,
        no_manual_boost=True,
        use_old_players_data=False,
        use_old_teams_data=False,
        use_comunio_price=True,
        biwenger_file_name="biwenger_laliga_data",
        elo_ratings_file_name="elo_ratings_laliga_data",
        ratings_file_name="sofascore_laliga_players_ratings",
        penalty_takers_file_name="transfermarket_laliga_penalty_takers",
        penalty_saves_file_name="transfermarket_laliga_penalty_savers",
        team_history_file_name="transfermarket_laliga_team_history",
        laligafantasy_file_name="laligafantasy_laliga_data",
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
        forced_matches=selected_jornada
    )
    if not disable_multi_jornada:
        jornada_index = list(display_to_key.keys()).index(selected_display_jornada)
        next_jornada_key = None
        if selected_num_jornadas >= 2:
            next_jornada_key = list(display_to_key.values())[jornada_index + 1] if jornada_index + 1 < len(
                display_to_key) else None
        next_next_jornada_key = None
        if selected_num_jornadas >= 3:
            next_next_jornada_key = list(display_to_key.values())[jornada_index + 2] if jornada_index + 2 < len(
                display_to_key) else None
        if next_jornada_key:
            with st.spinner("Cargando jugadores siguiente jornada..."):
                future_players = get_current_players(
                    no_form=True,
                    no_fixtures=False,
                    no_home_boost=False,
                    no_team_history_boost=False,
                    alt_fixture_method=False,
                    use_laligafantasy_data=not is_biwenger,
                    # alt_positions=not is_biwenger,
                    # alt_prices=not is_biwenger,
                    # alt_price_trends=not is_biwenger,
                    # alt_forms=not is_biwenger,
                    add_start_probability=True,
                    no_penalty_takers_boost=False,
                    nerf_penalty_boost=ignore_penalties,
                    no_penalty_savers_boost=False,
                    no_team_status_nerf=False,
                    no_manual_boost=True,
                    use_old_players_data=False,
                    use_old_teams_data=False,
                    use_comunio_price=True,
                    biwenger_file_name="biwenger_laliga_data",
                    elo_ratings_file_name="elo_ratings_laliga_data",
                    ratings_file_name="sofascore_laliga_players_ratings",
                    penalty_takers_file_name="transfermarket_laliga_penalty_takers",
                    penalty_saves_file_name="transfermarket_laliga_penalty_savers",
                    team_history_file_name="transfermarket_laliga_team_history",
                    laligafantasy_file_name="laligafantasy_laliga_data",
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
                    forced_matches=jornadas_dict[next_jornada_key],
                )
        if next_next_jornada_key:
            with st.spinner("Cargando jugadores siguientes jornadas..."):
                distant_players = get_current_players(
                    no_form=True,
                    no_fixtures=False,
                    no_home_boost=False,
                    no_team_history_boost=False,
                    alt_fixture_method=False,
                    use_laligafantasy_data=not is_biwenger,
                    # alt_positions=not is_biwenger,
                    # alt_prices=not is_biwenger,
                    # alt_price_trends=not is_biwenger,
                    # alt_forms=not is_biwenger,
                    add_start_probability=True,
                    no_penalty_takers_boost=False,
                    nerf_penalty_boost=ignore_penalties,
                    no_penalty_savers_boost=False,
                    no_team_status_nerf=False,
                    no_manual_boost=True,
                    use_old_players_data=False,
                    use_old_teams_data=False,
                    use_comunio_price=True,
                    biwenger_file_name="biwenger_laliga_data",
                    elo_ratings_file_name="elo_ratings_laliga_data",
                    ratings_file_name="sofascore_laliga_players_ratings",
                    penalty_takers_file_name="transfermarket_laliga_penalty_takers",
                    penalty_saves_file_name="transfermarket_laliga_penalty_savers",
                    team_history_file_name="transfermarket_laliga_team_history",
                    laligafantasy_file_name="laligafantasy_laliga_data",
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
                    forced_matches=jornadas_dict[next_next_jornada_key],
                )
        if selected_num_jornadas == 2:
            for cp in current_players:
                for fp in future_players:
                    if cp.name == fp.name:
                        cp.value = (cp.value + fp.value) / 2
                        cp.form = (cp.form + fp.form) / 2
                        cp.fixture = (cp.fixture + fp.fixture) / 2
        elif selected_num_jornadas == 3:
            for cp in current_players:
                for fp in future_players:
                    for dp in distant_players:
                        if cp.name == fp.name == dp.name:
                            cp.value = (cp.value + fp.value + dp.value) / 3
                            cp.form = (cp.form + fp.form + dp.form) / 3
                            cp.fixture = (cp.fixture + fp.fixture + dp.fixture) / 3

    current_team_list = sorted(set(player.team for player in current_players))


st.markdown(f"""
    <style>
    /* Ocultar el botón de fullscreen de todas las st.image */
    div[data-testid="stElementToolbar"] {{
        display: none;
    }}
    </style>
""", unsafe_allow_html=True)

# if main_option == "Mejores 11s con presupuesto" or main_option == "💰 Mejores 11s con presupuesto":
with tabs[0]:
    st.header("Mejores 11s dentro de tu presupuesto")

    with st.expander("Blindar o Excluir jugadores"):
        current_players_copy = copy.deepcopy(current_players)
        if "blinded_players_set" not in st.session_state:
            st.session_state.blinded_players_set = set()
        if "banned_players_set" not in st.session_state:
            st.session_state.banned_players_set = set()

        st.markdown("### 🔒 Jugadores blindados")
        st.caption("Estos jugadores estarán **sí o sí** en todos los equipos calculados")
        st.caption("_(siempre que entren dentro del presupuesto seleccionado)_")
        blinded_candidates = [p.name for p in current_players_copy if p.name not in st.session_state.blinded_players_set]
        selected_blindado = st.selectbox("Añadir jugador blindado", options=[""] + blinded_candidates, format_func=lambda x: normalize_name(x), key="add_blindado")
        if selected_blindado:
            st.session_state.blinded_players_set.add(selected_blindado)
            st.session_state.banned_players_set.discard(selected_blindado)
            st.rerun()

        blinded_players_list = [p for p in current_players_copy if p.name in st.session_state.blinded_players_set]
        # Ordenar jugadores
        blinded_players_list = sort_players(blinded_players_list, sort_option)
        # Mostrar blindados actuales
        for i, p in enumerate(blinded_players_list):
            # cols = st.columns([1, 5, 1])
            # with cols[0]:
            #     st.image(p.img_link, width=60)
            cols = st.columns([9, 1])
            with cols[0]:
                show_price = p.price
                if is_biwenger:
                    show_price = show_price / 10
                # st.markdown(f"- **{p.name}**: {p.position}, {p.team} – {show_price}M💰 {p.value:.3f} pts --> ({p.start_probability*100:.0f} %)")
                # st.markdown(f"- {p}")
                print_player(p, small_size=3)
            with cols[1]:
                if st.button("❌", key=f"remove_blindado_{i}"):
                    st.session_state.blinded_players_set.remove(p.name)
                    blinded_players_list.remove(p)
                    st.rerun()

        st.markdown("### 🚫 Jugadores excluidos")
        st.caption("Estos jugadores **no estarán bajo ningún concepto** en ningún equipo calculado")
        banned_candidates = [p.name for p in current_players_copy if p.name not in st.session_state.banned_players_set]
        selected_baneado = st.selectbox("Añadir jugador excluido", options=[""] + banned_candidates, format_func=lambda x: normalize_name(x), key="add_baneado")
        if selected_baneado:
            st.session_state.banned_players_set.add(selected_baneado)
            st.session_state.blinded_players_set.discard(selected_baneado)
            st.rerun()

        banned_players_list = [p for p in current_players_copy if p.name in st.session_state.banned_players_set]
        # Ordenar jugadores
        banned_players_list = sort_players(banned_players_list, sort_option)
        # Mostrar baneados actuales
        for i, p in enumerate(banned_players_list):
            # cols = st.columns([1, 5, 1])
            # with cols[0]:
            #     st.image(p.img_link, width=60)
            cols = st.columns([9, 1])
            with cols[0]:
                show_price = p.price
                if is_biwenger:
                    show_price = show_price / 10
                # st.markdown(f"- **{p.name}**: {p.position}, {p.team} – {show_price}M💰 {p.value:.3f} pts --> ({p.start_probability*100:.0f} %)")
                # st.markdown(f"- {p}")
                print_player(p, small_size=1)
            with cols[1]:
                if st.button("❌", key=f"remove_baneado_{i}"):
                    st.session_state.banned_players_set.remove(p.name)
                    banned_players_list.remove(p)
                    st.rerun()

    if is_biwenger:
        budget = st.number_input("Presupuesto máximo disponible", min_value=-1.0, max_value=100.0, value=30.0, step=0.1, key="budget_cap", format="%.1f")
        budget = int(budget * 10)
    else:
        budget = st.number_input("Presupuesto máximo disponible", min_value=-1, max_value=1000, value=200, step=1, key="budget_cap")
    st.caption("Pon **-1** si quieres indicar presupuesto ilimitado")
    # if is_biwenger:
    #     st.markdown(f"En Biwenger: **{budget / 10:.1f}M**")

    with st.expander("**Filtros adicionales**", expanded=True):
        use_fixture_filter = st.radio(
            "Excluir jugadores con partidos difíciles", ["No", "Sí"], index=0 if is_biwenger else 1,key="fixture_filter_budget"
        ) == "Sí"
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 65, key="prob_threshold_budget")
        # threshold = threshold_slider / 100
        prob_key = "prob_threshold_budget"
        min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, (65, 100), key=prob_key)
        max_prob_slider = 100
        st.markdown(f"""
            <style>
            /* Ocultar el segundo handle (derecho) del slider */
            div[class*="st-key-{prob_key}"] div[data-baseweb="slider"] div[role="slider"]:nth-child(2) {{
                display: none;
            }}
            </style>
        """, unsafe_allow_html=True)
        min_prob = min_prob_slider / 100
        max_prob = max_prob_slider / 100

        use_slow_calc = st.checkbox("Cálculo avanzado", value=False, key="is_slow_calc")
        st.caption("El cálculo será **mucho más lento** si se activa, pero usará casi todos los jugadores disponibles")

    use_premium = st.checkbox("Formaciones Premium", value=False, key="premium_budget")

    my_filtered_players = purge_everything(
        current_players_copy,
        probability_threshold=min_prob,
        fixture_filter=use_fixture_filter
    )
    my_filtered_players_names = [p.name for p in my_filtered_players]
    my_filtered_players = [
        p for p in current_players_copy
        if (p.name in my_filtered_players_names and min_prob <= p.start_probability <= max_prob) or (
                p.name in st.session_state.blinded_players_set
        )
    ]

    for player in my_filtered_players:
        if player.name in st.session_state.blinded_players_set:
            # player.price = 0
            player.value = max(1000, player.value*1000)
            player.start_probability = 10
            player.form = 10
            player.fixture = 10
        if player.name in st.session_state.banned_players_set:
            my_filtered_players.remove(player)

    possible_formations = [
        [3, 4, 3],
        [3, 5, 2],
        [4, 3, 3],
        [4, 4, 2],
        [4, 5, 1],
        [5, 3, 2],
        [5, 4, 1],
    ]
    if use_premium:
        possible_formations += [
            [3, 3, 4],
            [3, 6, 1],
            [4, 2, 4],
            [4, 6, 0],
            [5, 2, 3],
        ]

    if st.button("Calcular 11s", key="submit_budget_11") and my_filtered_players:
        st.markdown("## Mejores combinaciones posibles dentro del presupuesto:")
        worthy_players = sorted(
            my_filtered_players,
            key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
            reverse=False
        )
        needed_purge = worthy_players[:200]
        formation_score_players_by_score = best_full_teams(
            needed_purge,
            possible_formations,
            budget,
            verbose=2,
            speed_up=not use_slow_calc,
        )

        display_valid_formations(formation_score_players_by_score, current_players, st.session_state.blinded_players_set)

# Funcionalidades futuras
# elif main_option == "Mi mejor 11 posible" or main_option == "⚽ Mi mejor 11 posible":
with tabs[1]:
    st.header("Selecciona Jugadores para tu 11 ideal")
    st.caption("Añade a **todos** los jugadores de tu equipo para calcular tu 11 ideal")

    current_players = sorted(
        current_players,
        key=lambda x: (-x.price, -x.value, -x.form, -x.fixture, x.team),
        reverse=False
    )

    # Estado persistente para la lista de jugadores seleccionados
    if "my_players_names" not in st.session_state:
        st.session_state.my_players_names = set()
    if "blinded_players" not in st.session_state:
        st.session_state.blinded_players = set()

    # Búsqueda por autocompletado
    # player_names = [p.name for p in current_players]
    player_names = [p.name for p in current_players if p.name not in st.session_state.my_players_names]
    selected_name = st.selectbox("Buscar jugador", options=[""] + player_names, format_func=lambda x: normalize_name(x), key="busca_jugador")
    if selected_name not in st.session_state.my_players_names:
        st.session_state.my_players_names.add(selected_name)
        st.rerun()

    # Reconstruir lista de objetos player
    current_players_copy = copy.deepcopy(current_players)
    my_players_list = [p for p in current_players_copy if p.name in st.session_state.my_players_names]

    # Mostrar jugadores seleccionados
    if my_players_list:
        st.markdown("### Jugadores seleccionados:")
        st.caption("_Nota: 'Blindar' jugadores obliga a que estén **sí o sí** en todos los equipos calculados_")
        # Ordenar jugadores
        my_players_list = sort_players(my_players_list, sort_option)
        my_players_list_show = copy.deepcopy(my_players_list)
        for i, p in enumerate(my_players_list_show):
            cols = st.columns([8, 1, 2])
            # with cols[0]:
            #     st.image(p.img_link, width=70)
            with cols[0]:
                if is_biwenger:
                    p.price = p.price / 10
                # st.markdown(f"**{p.name}** - {p.position} - {p.team} - {p.price}M - {p.value} pts")
                # st.markdown(f"{p}")
                print_player(p, small_size=3)
            with cols[1]:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.my_players_names.remove(p.name)
                    st.session_state.blinded_players.discard(p.name)
                    st.rerun()
            with cols[2]:
                is_blinded = p.name in st.session_state.blinded_players
                blindar_label = "🔒 Blindado" if is_blinded else "Blindar"
                if st.button(blindar_label, key=f"blindar_{i}"):
                    if is_blinded:
                        st.session_state.blinded_players.remove(p.name)
                    else:
                        st.session_state.blinded_players.add(p.name)
                    st.rerun()

        for p in my_players_list:
            # Aplicar valores si está blindado
            if p.name in st.session_state.blinded_players:
                p.value = max(1000, p.value * 1000)
                p.start_probability = 10
                p.form = 10
                p.fixture = 10

    # Filtros adicionales aplicados sobre `my_players_list`
    with st.expander("**Filtros adicionales sobre tu lista**", expanded=True if my_players_list else 0):
        use_fixture_filter = st.radio(
            "Excluir jugadores con partidos difíciles", ["No", "Sí"], index=0 if is_biwenger else 1, key="fixture_filter_my11"
        ) == "Sí"
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 65, key="prob_threshold_my11")
        # threshold = threshold_slider / 100
        prob_key = "prob_threshold_my11"
        min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, (65, 100), key=prob_key)
        max_prob_slider = 100
        st.markdown(f"""
            <style>
            /* Ocultar el segundo handle (derecho) del slider */
            div[class*="st-key-{prob_key}"] div[data-baseweb="slider"] div[role="slider"]:nth-child(2) {{
                display: none;
            }}
            </style>
        """, unsafe_allow_html=True)
        min_prob = min_prob_slider / 100
        max_prob = max_prob_slider / 100

        filtered_players = purge_everything(
            my_players_list,
            probability_threshold=min_prob,
            fixture_filter=use_fixture_filter
        )
        filtered_players_names = [p.name for p in filtered_players]
        filtered_players = [
            p for p in my_players_list
            if (p.name in filtered_players_names and min_prob <= p.start_probability <= max_prob) or (
                    p.name in st.session_state.blinded_players
            )
        ]

    # Checkbox para formaciones premium
    use_premium = st.checkbox("Formaciones Premium", value=False)

    possible_formations = [
        [3, 4, 3],
        [3, 5, 2],
        [4, 3, 3],
        [4, 4, 2],
        [4, 5, 1],
        [5, 3, 2],
        [5, 4, 1],
    ]
    if use_premium:
        possible_formations += [
            [3, 3, 4],
            [3, 6, 1],
            [4, 2, 4],
            [4, 6, 0],
            [5, 2, 3],
        ]

    # Botón para ejecutar selección final
    if st.button("Listo", key="submit_my_11") and filtered_players:
        counts = Counter(player.position for player in filtered_players)
        position_counts = {pos: counts.get(pos, 0) for pos in ["GK", "DEF", "MID", "ATT"]}
        if use_premium:
            if position_counts["GK"] < 1:
                st.warning("Necesitas al menos 1 Portero.")
            if position_counts["DEF"] < 3:
                st.warning("Necesitas al menos 3 Defensas.")
            if position_counts["MID"] < 2:
                st.warning("Necesitas al menos 2 Mediocentros.")
            if position_counts["ATT"] < 0:
                st.warning("Necesitas al menos 0 Delanteros.")
            if position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] == 0:
                st.warning("Necesitas 5 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 4:
                st.warning("Necesitas 1 Defensa/Mediocentro más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 6 and position_counts["ATT"] == 0:
                st.warning("Necesitas 1 Defensa/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 4 and position_counts["ATT"] == 0:
                st.warning("Necesitas 1 Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 2 and position_counts["ATT"] == 2:
                st.warning("Necesitas 1 Mediocentro/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 5 and position_counts["ATT"] == 0:
                st.warning("Necesitas 1 Mediocentro/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 3:
                st.warning("Necesitas 1 Defensa/Mediocentro/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 5 and position_counts["ATT"] == 1:
                st.warning("Necesitas 1 Defensa/Mediocentro/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning("Necesitas 1 Mediocentro/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 3:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 5 and position_counts["ATT"] == 0:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 3 and position_counts["ATT"] == 0:
                st.warning("Necesitas 2 Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 2 and position_counts["ATT"] == 1:
                st.warning("Necesitas 2 Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 2:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 4 and position_counts["ATT"] == 1:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 2:
                st.warning("Necesitas 3 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 4 and position_counts["ATT"] == 0:
                st.warning("Necesitas 3 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 2 and position_counts["ATT"] == 0:
                st.warning("Necesitas 3 Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 4 and position_counts["MID"] == 3 and position_counts["ATT"] == 0:
                st.warning("Necesitas 3 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning("Necesitas 3 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 1:
                st.warning("Necesitas 4 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 3 and position_counts["ATT"] == 0:
                st.warning("Necesitas 4 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 2 and position_counts["ATT"] == 0:
                st.warning("Necesitas 4 Defensas/Mediocentros/Delanteros más")
            # else:
            #     if position_counts["GK"] >= 1 and position_counts["DEF"] >= 3 and position_counts["MID"] >= 2 and position_counts["ATT"] >= 0:
            #         st.warning("Necesitas al menos 1 Defensa/Mediocentro/Delantero más")
        else:
            if position_counts["GK"] < 1:
                st.warning("Necesitas al menos 1 Portero.")
            if position_counts["DEF"] < 3:
                st.warning("Necesitas al menos 3 Defensas.")
            if position_counts["MID"] < 3:
                st.warning("Necesitas al menos 3 Mediocentros.")
            if position_counts["ATT"] < 1:
                st.warning("Necesitas al menos 1 Delantero.")
            if position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning("Necesitas 3 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 3:
                st.warning("Necesitas 1 Defensa/Mediocentro más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 5 and position_counts["ATT"] == 1:
                st.warning("Necesitas 1 Defensa/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning("Necesitas 1 Mediocentro/Delantero más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 2:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 4 and position_counts["ATT"] == 1:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning("Necesitas 2 Defensas/Mediocentros/Delanteros más")
            # else:
            #     if position_counts["GK"] >= 1 and position_counts["DEF"] >= 3 and position_counts["MID"] >= 3 and position_counts["ATT"] >= 1:
            #         st.warning("Necesitas al menos 1 Defensa/Mediocentro/Delantero más")
        if len(filtered_players) < 11:
            if len(my_players_list) >= 11:
                st.warning("Filtros demasiado exigentes, selecciona menos filtros.")
            else:
                st.warning("Selecciona al menos 11 jugadores antes de continuar.")
        else:
            st.markdown("## Mejores combinaciones posibles:")
            worthy_players = sorted(
                filtered_players,
                key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
                reverse=False
            )
            formation_score_players_by_score = best_full_teams(
                worthy_players,
                possible_formations,
                -1,
                verbose=1
            )
            # print_best_full_teams(formation_score_players_by_score)
            display_valid_formations(formation_score_players_by_score, current_players, st.session_state.blinded_players)

# Si selecciona "Lista de jugadores"
# ekif main_option == "Lista de jugadores" or main_option == "📋 Lista de jugadores":
with tabs[2]:
    st.header("Lista de Jugadores Actualizada")
    st.markdown(
        """
            _· **Jugador** (Posición, Equipo): Precio - **Puntuación**_  
            _(Forma: estado de forma, Partido: complejidad del partido, Titular: probabilidad de ser titular %)_
        """
    )

    # Filtros adicionales
    with st.expander("Filtros adicionales"):
        use_fixture_filter = st.radio("Filtrar por dificultad de partido", ["No", "Sí"], index=0) == "Sí"
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 0)
        # threshold = threshold_slider / 100

        prob_key = "prob_threshold_playerslist"
        # if prob_key in st.session_state:
        #     min_val = st.session_state[prob_key][0]
        #     st.session_state[prob_key] = (min_val, 100)
        # else:
        #     st.session_state[prob_key] = (0, 100)
        # min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, value=st.session_state[prob_key], key=prob_key)
        min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, (0, 100), key=prob_key)
        max_prob_slider = 100
            # div[class*="st-key-prob_threshold_playerslist"] div[data-testid="stSlider"] > div > div > div > div:nth-child(2) {
            # div[class*="st-key-prob_threshold_playerslist"] div > div > div > div > div > div:nth-child(2) {
        st.markdown(f"""
            <style>
            /* Ocultar el segundo handle (derecho) del slider */
            div[class*="st-key-{prob_key}"] div[data-baseweb="slider"] div[role="slider"]:nth-child(2) {{
                display: none;
            }}
            </style>
        """, unsafe_allow_html=True)
        min_prob = min_prob_slider / 100
        max_prob = max_prob_slider / 100

        # Filtro por precio
        if is_biwenger:
            min_price, max_price = st.slider("Filtrar por precio (en M)", 0.0, 30.0, (0.0, 30.0), step=0.1, key="slider_precio", format="%.1f")
            min_price = int(min_price * 10)
            max_price = int(max_price * 10)
        else:
            min_price, max_price = st.slider("Filtrar por precio (en M)", 0, 300, (0, 300), step=1, key="slider_precio", format="%.0f")

        # Filtro por posición
        st.markdown("**Filtrar por posición:**")
        filter_gk = st.checkbox("Portero", value=True)
        filter_def = st.checkbox("Defensa", value=True)
        filter_mid = st.checkbox("Mediocentro", value=True)
        filter_att = st.checkbox("Delantero", value=True)

        filter_teams = st.multiselect("Filtrar por equipos", options=current_team_list, format_func=lambda x: normalize_name(x), placeholder="Selecciona uno o varios equipos")

        # Aplicar filtros
        current_players_filtered = [
            p for p in current_players
            if min_price <= p.price <= max_price and (
                (filter_gk and p.position == "GK") or
                (filter_def and p.position == "DEF") or
                (filter_mid and p.position == "MID") or
                (filter_att and p.position == "ATT")
            ) and min_prob <= p.start_probability <= max_prob and (
                not filter_teams or p.team in filter_teams
            )
        ]

        if use_fixture_filter != False or min_prob_slider != 0:
            current_players_filtered = purge_everything(
                current_players_filtered,
                probability_threshold=min_prob,
                fixture_filter=use_fixture_filter
            )

    # Ordenar jugadores
    current_players_filtered = sort_players(current_players_filtered, sort_option)

    # Mostrar resultados
    num_jugadores = len(current_players_filtered)
    jugador_texto = "jugador" if num_jugadores == 1 else "jugadores"
    st.subheader(
        f"{num_jugadores} {jugador_texto} encontrado" + ("s" if num_jugadores != 1 else "")
    )

    show_players = copy.deepcopy(current_players_filtered)
    for player in show_players:
        if is_biwenger:
            player.price = player.price / 10
        # st.text(str(player))
        print_player(player)

with tabs[3]:
    st.header("Selecciona los Jugadores de tu mercado")
    st.caption("Selecciona los Jugadores que han salido en tu mercado para compararlos entre ellos")
    st.caption("_Nota: es lo mismo que la 'Lista de jugadores', pero seleccionando solo a los jugadores que quieres ver_")

    current_players = sorted(
        current_players,
        key=lambda x: (-x.price, -x.value, -x.form, -x.fixture, x.team),
        reverse=False
    )

    # Estado persistente para la lista de jugadores seleccionados
    if "my_players_names_set" not in st.session_state:
        st.session_state.my_players_names_set = set()

    # Búsqueda por autocompletado
    # player_names = [p.name for p in current_players]
    player_names = [p.name for p in current_players if p.name not in st.session_state.my_players_names_set]
    selected_name = st.selectbox("Buscar jugador", options=[""] + player_names, format_func=lambda x: normalize_name(x), key="busca_mercado")
    if selected_name not in st.session_state.my_players_names_set:
        st.session_state.my_players_names_set.add(selected_name)
        st.rerun()

    # Reconstruir lista de objetos player
    current_players_copy = copy.deepcopy(current_players)
    my_market_players_list = [p for p in current_players_copy if p.name in st.session_state.my_players_names_set]

    # Mostrar jugadores seleccionados
    if my_market_players_list:
        # Filtros adicionales aplicados sobre `my_market_players_list`
        with st.expander("Filtros adicionales sobre tu lista"):
            use_fixture_filter = st.radio("Filtrar por dificultad de partido", ["No", "Sí"], index=0, key="fixture_filter") == "Sí"
            prob_key = "prob_threshold_marketplayerslist"
            min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, (0, 100), key=prob_key)
            max_prob_slider = 100
            st.markdown(f"""
                <style>
                /* Ocultar el segundo handle (derecho) del slider */
                div[class*="st-key-{prob_key}"] div[data-baseweb="slider"] div[role="slider"]:nth-child(2) {{
                    display: none;
                }}
                </style>
            """, unsafe_allow_html=True)
            min_prob = min_prob_slider / 100
            max_prob = max_prob_slider / 100

            # Filtro por precio
            if is_biwenger:
                min_price, max_price = st.slider("Filtrar por precio (en M)", 0.0, 30.0, (0.0, 30.0), step=0.1, key="slider_precio_market", format="%.1f")
                min_price = int(min_price * 10)
                max_price = int(max_price * 10)
            else:
                min_price, max_price = st.slider("Filtrar por precio (en M)", 0, 300, (0, 300), step=1, key="slider_precio_market", format="%.0f")

            # Filtro por posición
            st.markdown("**Filtrar por posición:**")
            filter_gk = st.checkbox("Portero", value=True, key="filter_gk")
            filter_def = st.checkbox("Defensa", value=True, key="filter_def")
            filter_mid = st.checkbox("Mediocentro", value=True, key="filter_mid")
            filter_att = st.checkbox("Delantero", value=True, key="filter_att")

            filter_teams = st.multiselect("Filtrar por equipos", options=current_team_list, format_func=lambda x: normalize_name(x), placeholder="Selecciona uno o varios equipos", key="multichoice_teams")

            # Aplicar filtros
            my_market_filtered_players_list = [
                p for p in my_market_players_list
                if min_price <= p.price <= max_price and (
                        (filter_gk and p.position == "GK") or
                        (filter_def and p.position == "DEF") or
                        (filter_mid and p.position == "MID") or
                        (filter_att and p.position == "ATT")
                ) and min_prob <= p.start_probability <= max_prob and (
                    not filter_teams or p.team in filter_teams
                )
            ]

            if use_fixture_filter != False or min_prob_slider != 0:
                my_market_filtered_players_list = purge_everything(
                    my_market_filtered_players_list,
                    probability_threshold=min_prob,
                    fixture_filter=use_fixture_filter
                )
            num_filtrados = len(my_market_players_list) - len(my_market_filtered_players_list)

        # Mostrar resultados
        num_jugadores = len(my_market_filtered_players_list)
        jugador_texto = "jugador" if num_jugadores == 1 else "jugadores"
        filtrado_texto = "filtrado" if num_filtrados == 1 else "filtrados"
        st.subheader(
            f"{num_jugadores} {jugador_texto} seleccionado" + ("s" if num_jugadores != 1 else "") + f" _({num_filtrados} {filtrado_texto})_"
        )
        st.caption("_Nota: ten en cuenta que la 'Forma' se calcula en función de cómo sube o baja el precio del jugador_")

        # Ordenar jugadores
        my_market_filtered_players_list = sort_players(my_market_filtered_players_list, sort_option)
        my_market_filtered_players_list_show = copy.deepcopy(my_market_filtered_players_list)
        for i, p in enumerate(my_market_filtered_players_list_show):
            cols = st.columns([9, 1])
            # with cols[0]:
            #     st.image(p.img_link, width=60)
            with cols[0]:
                if is_biwenger:
                    p.price = p.price / 10
                # st.markdown(f"**{p.name}** - {p.position} - {p.team} - {p.price}M - {p.value} pts")
                # st.markdown(f"{p}")
                print_player(p, small_size=1)
            with cols[1]:
                if st.button("❌", key=f"market_remove_{i}"):
                    st.session_state.my_players_names_set.remove(p.name)
                    st.session_state.blinded_players.discard(p.name)
                    st.rerun()
        # for player in my_market_filtered_players_list_show:
        #     if is_biwenger:
        #         player.price = player.price / 10
        #     st.text(str(player))
    else:
        my_market_filtered_players_list = []


st.markdown("---")

# st.markdown(
#     "By pabloroldan98 (Twitch: DonRoda)"
# )
st.markdown("📩 Contacto: [calculadora.fantasy@gmail.com](mailto:calculadora.fantasy@gmail.com)")

# Auto-update trigger: Fri Aug  8 22:25:00 UTC 2025
