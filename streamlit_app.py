import streamlit as st

from group_knapsack import print_best_full_teams, best_full_teams
from main import get_current_players, purge_everything
from useful_functions import read_dict_data

st.title("Calculadora Fantasy")
st.markdown(
    "By pabloroldan98"
)

tab_labels = [
    "📋 Lista de jugadores",
    "⚽ Mi mejor 11 posible",
    "💰 Mejores 11s con presupuesto"
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
app_option = st.sidebar.selectbox("Aplicación", ["LaLiga Fantasy", "Biwenger"], index=0)
penalties_option = st.sidebar.radio("¿Te importan los penaltis?", ["Sí", "No"], index=0)
sort_option = st.sidebar.selectbox("Ordenar por", ["Puntuación", "Rentabilidad", "Precio", "Forma", "Partido", "Probabilidad"], index=0)

# Jornada
jornadas_dict = read_dict_data("forced_matches_laliga_2025_26")
display_to_key = {key.replace("_", " ").strip().title(): key for key in jornadas_dict}
display_options = ["Siguiente partido"] + list(display_to_key.keys())
selected_display_jornada = st.sidebar.selectbox("Jornada", options=display_options, index=0)
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
        alt_positions=not is_biwenger,
        alt_prices=not is_biwenger,
        alt_price_trends=not is_biwenger,
        alt_forms=not is_biwenger,
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
                    alt_positions=not is_biwenger,
                    alt_prices=not is_biwenger,
                    alt_price_trends=not is_biwenger,
                    alt_forms=not is_biwenger,
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
                    alt_positions=not is_biwenger,
                    alt_prices=not is_biwenger,
                    alt_price_trends=not is_biwenger,
                    alt_forms=not is_biwenger,
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

# Si selecciona "Lista de jugadores"
# if main_option == "Lista de jugadores" or main_option == "📋 Lista de jugadores":
with tabs[0]:
    st.header("Lista de Jugadores Actualizada")
    st.markdown(
        "_Ejemplo: (Jugador, Posición, Equipo, Precio, Puntuación, Estado) - "
        "(form: coeficiente_forma, fixture: coeficiente_partido) --> Probabilidad de que juegue %_"
    )

    # Filtros adicionales
    with st.expander("Filtros adicionales"):
        use_fixture_filter = st.radio("Filtrar por dificultad de partido", ["No", "Sí"], index=0) == "Sí"
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 0)
        # threshold = threshold_slider / 100
        min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, (0, 100))
        min_prob = min_prob_slider / 100
        max_prob = max_prob_slider / 100

        # Filtro por precio
        min_price, max_price = st.slider("Filtrar por precio (en M)", 0, 300, (0, 300))
        if is_biwenger:
            st.markdown(f"En Biwenger: **De {min_price / 10:.1f}M - a {max_price / 10:.1f}M**")

        # Filtro por posición
        st.markdown("**Filtrar por posición:**")
        filter_gk = st.checkbox("Portero", value=True)
        filter_def = st.checkbox("Defensa", value=True)
        filter_mid = st.checkbox("Mediocentro", value=True)
        filter_att = st.checkbox("Delantero", value=True)

        # Aplicar filtros
        current_players = [
            p for p in current_players
            if min_price <= p.price <= max_price and (
                (filter_gk and p.position == "GK") or
                (filter_def and p.position == "DEF") or
                (filter_mid and p.position == "MID") or
                (filter_att and p.position == "ATT")
            ) and min_prob <= p.start_probability <= max_prob
        ]

        if use_fixture_filter != False or min_prob_slider != 0:
            current_players = purge_everything(
                current_players,
                probability_threshold=min_prob,
                fixture_filter=use_fixture_filter
            )

    # Ordenar jugadores
    if sort_option == "Rentabilidad":
        current_players = sorted(
            current_players,
            key=lambda x: (x.value - 7) / max(x.price, 1),
            reverse=True
        )
    elif sort_option == "Precio":
        current_players = sorted(
            current_players,
            key=lambda x: (-x.price, -x.value, -x.form, -x.fixture, x.team),
            reverse=False
        )
    elif sort_option == "Forma":
        current_players = sorted(
            current_players,
            key=lambda x: (-x.form, -x.value, -x.fixture, x.price, x.team),
            reverse=False
        )
    elif sort_option == "Partido":
        current_players = sorted(
            current_players,
            key=lambda x: (-x.fixture, -x.value, -x.form, x.price, x.team),
            reverse=False
        )
    elif sort_option == "Probabilidad":
        current_players = sorted(
            current_players,
            key=lambda x: (-x.start_probability, -x.value, -x.form, -x.fixture, x.price, x.team),
            reverse=False
        )
    else:  # Puntuación
        current_players = sorted(
            current_players,
            key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
            reverse=False
        )

    # Mostrar resultados
    st.subheader(f"{len(current_players)} jugadores encontrados")

    for player in current_players:
        if is_biwenger:
            player.price = player.price / 10
        st.text(str(player))

# Funcionalidades futuras
# elif main_option == "Mi mejor 11 posible" or main_option == "⚽ Mi mejor 11 posible":
with tabs[1]:
    st.header("Selecciona Jugadores para tu 11 ideal")

    current_players = sorted(
        current_players,
        key=lambda x: (-x.price, -x.value, -x.form, -x.fixture, x.team),
        reverse=False
    )

    # Estado persistente para la lista de jugadores seleccionados
    if "my_players_names" not in st.session_state:
        st.session_state.my_players_names = []
    if "last_selected_name" not in st.session_state:
        st.session_state.last_selected_name = None
    if "needs_reset" not in st.session_state:
        st.session_state.needs_reset = False
    if "blinded_players" not in st.session_state:
        st.session_state.blinded_players = set()

    # Búsqueda por autocompletado
    player_names = [p.name for p in current_players]
    if st.session_state.needs_reset:
        st.session_state.busca_jugador = ""
        st.session_state.last_selected_name = None
        st.session_state.needs_reset = False
        # st.rerun()
    selected_name = st.selectbox("Buscar jugador", options=[""] + player_names, key="busca_jugador")
    if st.session_state.last_selected_name == selected_name:
        st.session_state.needs_reset = True

    if selected_name and st.session_state.last_selected_name != selected_name:
        if selected_name not in st.session_state.my_players_names:
            st.session_state.my_players_names.append(selected_name)
            st.session_state.last_selected_name = selected_name

    # Reconstruir lista de objetos player
    my_players_list = [p for p in current_players if p.name in st.session_state.my_players_names]

    # Mostrar jugadores seleccionados
    if my_players_list:
        st.markdown("### Jugadores seleccionados:")
        my_players_list = sorted(
            my_players_list,
            key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
            reverse=False
        )
        # Ordenar jugadores
        if sort_option == "Rentabilidad":
            my_players_list = sorted(
                my_players_list,
                key=lambda x: (x.value - 7) / max(x.price, 1),
                reverse=True
            )
        elif sort_option == "Precio":
            my_players_list = sorted(
                my_players_list,
                key=lambda x: (-x.price, -x.value, -x.form, -x.fixture, x.team),
                reverse=False
            )
        elif sort_option == "Forma":
            my_players_list = sorted(
                my_players_list,
                key=lambda x: (-x.form, -x.value, -x.fixture, x.price, x.team),
                reverse=False
            )
        elif sort_option == "Partido":
            my_players_list = sorted(
                my_players_list,
                key=lambda x: (-x.fixture, -x.value, -x.form, x.price, x.team),
                reverse=False
            )
        elif sort_option == "Probabilidad":
            my_players_list = sorted(
                my_players_list,
                key=lambda x: (-x.start_probability, -x.value, -x.form, -x.fixture, x.price, x.team),
                reverse=False
            )
        else:  # Puntuación
            my_players_list = sorted(
                my_players_list,
                key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
                reverse=False
            )
        for i, p in enumerate(my_players_list):
            cols = st.columns([1, 4, 1, 1])
            with cols[0]:
                st.image(p.img_link, width=70)
            with cols[1]:
                # st.markdown(f"**{p.name}** - {p.position} - {p.team} - {p.price}M - {p.value} pts")
                st.markdown(f"{p}")
            with cols[2]:
                if st.button("❌", key=f"remove_{i}"):
                    my_players_list.remove(p)
                    st.session_state.my_players_names.remove(p.name)
                    st.session_state.blinded_players.discard(p.name)
                    st.rerun()
            with cols[3]:
                is_blinded = p.name in st.session_state.blinded_players
                blindar_label = "🔒 Blindado" if is_blinded else "Blindar"
                if st.button(blindar_label, key=f"blindar_{i}"):
                    if is_blinded:
                        st.session_state.blinded_players.remove(p.name)
                    else:
                        st.session_state.blinded_players.add(p.name)
                    st.rerun()

            # Aplicar valores si está blindado
            if p.name in st.session_state.blinded_players:
                p.value = 1000
                p.start_probability = 10
                p.form = 10
                p.fixture = 10

        # Filtros adicionales aplicados sobre `my_players_list`
        with st.expander("Filtros adicionales sobre tu lista"):
            use_fixture_filter = st.radio("Filtrar por dificultad de partido", ["No", "Sí"], index=1, key="fixture_filter_my11") == "Sí"
            # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 65, key="threshold_my11")
            # threshold = threshold_slider / 100
            min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, (65, 100), key="threshold_my11")
            min_prob = min_prob_slider / 100
            max_prob = max_prob_slider / 100

            filtered_players = purge_everything(
                my_players_list,
                probability_threshold=min_prob,
                fixture_filter=use_fixture_filter
            )
            filtered_players = [
                p for p in filtered_players
                if min_prob <= p.start_probability <= max_prob
            ]
    else:
        filtered_players = []

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
        if len(filtered_players) < 11:
            if 11 <= len(my_players_list):
                st.warning("Filtros demasiado exigentes, selecciona menos filtros.")
            else:
                st.warning("Selecciona al menos 11 jugadores antes de continuar.")
        else:
            st.markdown("## Mejores combinaciones posibles:")
            formation_score_players_by_score = best_full_teams(
                filtered_players,
                possible_formations,
                -1,
                verbose=1
            )
            # print_best_full_teams(formation_score_players_by_score)
            valid_formations = [
                (formation, round(score, 3), players)
                for formation, score, players in formation_score_players_by_score
                if score != -1
            ]

            for formation, score, players in valid_formations:
                st.markdown(f"### Formación {formation}: {score} puntos")

                # Organizar jugadores por posición
                lines = {
                    "ATT": [],
                    "MID": [],
                    "DEF": [],
                    "GK": [],
                }

                for player in players:
                    lines[player.position].append(player)

                # Mostrar jugadores en orden de líneas
                for position in ["ATT", "MID", "DEF", "GK"]:
                    if lines[position]:
                        cols = st.columns(len(lines[position]), gap="small")
                        for i, player in enumerate(lines[position]):
                            with cols[i]:
                                st.markdown(
                                    f"""
                                    <div style='text-align:center'>
                                        <img src='{player.img_link}' width='70'><br>
                                        {player.name} ({player.start_probability * 100:.0f}%)
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                # Mostrar lista textual expandible debajo
                with st.expander("Ver todos los jugadores utilizados"):
                    for player in players:
                        st.markdown(f"- {player}")

                st.markdown("---")  # Separador entre formaciones

# elif main_option == "Mejores 11s con presupuesto" or main_option == "💰 Mejores 11s con presupuesto":
with tabs[2]:
    st.header("Mejores 11s dentro de tu presupuesto")

    with st.expander("Filtros adicionales"):
        use_fixture_filter = st.radio("Filtrar por dificultad de partido", ["No", "Sí"], index=1, key="fixture_filter_budget") == "Sí"
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 65, key="threshold_budget")
        # threshold = threshold_slider / 100
        min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, (65, 100), key="threshold_budget")
        min_prob = min_prob_slider / 100
        max_prob = max_prob_slider / 100

    use_premium = st.checkbox("Formaciones Premium", value=False, key="premium_budget")

    budget = st.number_input("Presupuesto máximo disponible", min_value=-1, max_value=1000, value=200, step=1, key="budget_cap")
    st.caption("Pon **-1** si quieres indicar presupuesto ilimitado")
    if is_biwenger:
        st.markdown(f"En Biwenger: **{budget / 10:.1f}M**")

    filtered_players = purge_everything(
        current_players,
        probability_threshold=min_prob,
        fixture_filter=use_fixture_filter
    )
    filtered_players = [
        p for p in filtered_players
        if min_prob <= p.start_probability <= max_prob
    ]

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

    if st.button("Calcular 11s", key="submit_budget_11") and filtered_players:
        st.markdown("## Mejores combinaciones posibles dentro del presupuesto:")
        worthy_players = sorted(
            filtered_players,
            key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
            reverse=False
        )
        needed_purge = worthy_players[:150]
        formation_score_players_by_score = best_full_teams(
            needed_purge,
            possible_formations,
            budget,
            verbose=2
        )

        valid_formations = [
            (formation, round(score, 3), players)
            for formation, score, players in formation_score_players_by_score
            if score != -1
        ]

        for formation, score, players in valid_formations:
            total_price = sum(player.price for player in players)
            show_price = total_price / 10 if is_biwenger else total_price
            st.markdown(f"### Formación {formation}: {score:.3f} puntos – 💰 {show_price}M")

            lines = {"ATT": [], "MID": [], "DEF": [], "GK": []}
            for player in players:
                lines[player.position].append(player)

            for position in ["ATT", "MID", "DEF", "GK"]:
                if lines[position]:
                    cols = st.columns(len(lines[position]), gap="small")
                    for i, player in enumerate(lines[position]):
                        with cols[i]:
                            st.markdown(
                                f"""
                                <div style='text-align:center'>
                                    <img src='{player.img_link}' width='70'><br>
                                    {player.name} ({player.start_probability * 100:.0f}%)
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

            with st.expander("Ver todos los jugadores utilizados"):
                for player in players:
                    st.markdown(f"- {player}")

            st.markdown("---")

