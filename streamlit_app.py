import os
import copy
import json
import html
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
import requests
from PIL import Image
from unidecode import unidecode
from collections import Counter

from group_knapsack import print_best_full_teams, best_full_teams
from main import get_current_players, purge_everything
from useful_functions import read_dict_data, percentile_ranks_dict, percentile_rank
from biwenger import get_next_jornada

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


SUPPORTED_LANGS = ("es", "en")

# Put every visible string behind a key. You can grow this dict over time.
I18N = {
    # App
    "app.title": {"es": "Calculadora Fantasy 🤖", "en": "Fantasy Calculator 🤖"},
    "app.hero_logo_alt": {"es": "Logo Calculadora", "en": "Calculator Logo"},
    "app.laligafantasy": {"es": "LaLiga Fantasy", "en": "LaLiga Fantasy"},
    "app.biwenger": {"es": "Biwenger", "en": "Biwenger"},

    # Tabs
    "tab.best11_budget": {"es": "💰 Mejores 11s con presupuesto", "en": "💰 Best lineups by budget"},
    "tab.my_best11": {"es": "⚽ Mi mejor 11 posible", "en": "⚽ My best possible lineup"},
    "tab.players_list": {"es": "📋 Lista de jugadores", "en": "📋 Players list"},
    "tab.my_market": {"es": "📈 Analizar mi mercado", "en": "📈 Analyze my market"},

    # Sidebar
    "sb.options": {"es": "Opciones", "en": "Options"},
    "sb.app": {"es": "Aplicación", "en": "App"},
    "sb.penalties": {"es": "¿Te importan los penaltis?", "en": "Do penalties matter to you?"},
    "opt.yes": {"es": "Sí", "en": "Yes"},
    "opt.no": {"es": "No", "en": "No"},
    "sb.sort_by": {"es": "Ordenar por", "en": "Sort by"},
    "sort.score": {"es": "Puntuación", "en": "Score"},
    "sort.worth": {"es": "Rentabilidad", "en": "Worth"},
    "sort.price": {"es": "Precio", "en": "Price"},
    "sort.form": {"es": "Forma", "en": "Form"},
    "sort.fixture": {"es": "Partido", "en": "Fixture"},
    "sort.startprobability": {"es": "Probabilidad", "en": "Start probability"},
    "sort.position": {"es": "Posición", "en": "Position"},
    "sb.use_start_prob_with_value": {
        "es": "Utilizar '% Titular' cuando se Ordena por **Rentabilidad**",
        "en": "Use 'Start %' when sorting by **Worth**",
    },

    # Jornada / matches
    "sb.jornada": {"es": "Jornada", "en": "Matchweek"},
    "jornada.next": {"es": "Siguiente partido", "en": "Next match"},
    "sb.num_jornadas": {"es": "Cuántas jornadas tener en cuenta", "en": "How many matchweeks to consider"},
    "num.one": {"es": "Una jornada (solo la jornada elegida)", "en": "One matchweek (only the selected matchweek)"},
    "num.two": {"es": "Dos jornadas (jornada elegida +1)", "en": "Two matchweeks (selected matchweek +1)"},
    "num.three": {"es": "Tres jornadas (jornada elegida +2)", "en": "Three matchweeks (selected matchweek +2)"},
    "hint.select_specific_jornada": {
        "es": "Selecciona una jornada específica para usar varias jornadas.",
        "en": "Select a specific matchweek to use multiple matchweeks.",
    },

    # Toggles
    "sb.ignore_form": {"es": "¿Ignorar estado de **forma**?", "en": "Ignore **form**?"},
    "sb.ignore_fixtures": {"es": "¿Ignorar dificultad del **partido**?", "en": "Ignore **fixture difficulty**?"},

    # Budget section
    "h.budget11": {"es": "Mejores 11s dentro de tu presupuesto", "en": "Best lineups within your budget"},
    "sb.budget.max": {"es": "Presupuesto máximo disponible", "en": "Maximum available budget"},
    "sb.budget.hint": {"es": "Pon **-1** si quieres indicar presupuesto ilimitado", "en": "Use **-1** for unlimited budget"},
    "sb.extra_filters": {"es": "**Filtros adicionales**", "en": "**Additional filters**"},
    "sb.exclude_hard_fixtures": {
        "es": "Excluir jugadores con partidos difíciles",
        "en": "Exclude players with hard fixtures",
    },
    "sb.start_prob_range": {"es": "Probabilidad de ser titular (%)", "en": "Probability to start (%)"},
    "sb.slow_calc": {"es": "Cálculo avanzado", "en": "Advanced calculation"},
    "sb.slow_calc_hint": {
        "es": "El cálculo será **mucho más lento** si se activa, pero usará casi todos los jugadores disponibles",
        "en": "This is **much slower**, but uses almost all available players",
    },
    "sb.premium_formations": {"es": "Formaciones Premium", "en": "Premium formations"},
    "btn.calc11": {"es": "Calcular 11s", "en": "Calculate lineups"},
    "h.best_combinations_budget": {
        "es": "Mejores combinaciones posibles dentro del presupuesto:",
        "en": "Best combinations within budget:",
    },

    # Blinded / banned
    "blind.header": {"es": "Blindar o Excluir jugadores", "en": "Lock or Exclude players"},
    "blind.title": {"es": "🔒 Jugadores blindados", "en": "🔒 Locked players"},
    "blind.caption1": {
        "es": "Estos jugadores estarán **sí o sí** en todos los equipos calculados",
        "en": "These players will **always** be in every calculated team",
    },
    "blind.caption2": {
        "es": "_(siempre que entren dentro del presupuesto seleccionado)_",
        "en": "_(as long as they fit in your budget)_",
    },
    "blind.add": {"es": "Añadir jugador blindado", "en": "Add locked player"},
    "blind.total_price": {"es": "Precio total de jugadores blindados:", "en": "Total price of locked players:"},
    "ban.title": {"es": "🚫 Jugadores excluidos", "en": "🚫 Excluded players"},
    "ban.caption": {
        "es": "Estos jugadores **no estarán bajo ningún concepto** en ningún equipo calculado",
        "en": "These players will **never** be in any calculated team",
    },
    "ban.add": {"es": "Añadir jugador excluido", "en": "Add excluded player"},

    # Players list
    "h.players_list": {"es": "Lista de Jugadores Actualizada", "en": "Updated Players List"},
    "players.legend": {
        "es": "_· **Jugador** (Posición, Equipo): Precio - **Puntuación**_  \n_(Forma: estado de forma, Partido: complejidad del partido, Titular: probabilidad de ser titular %)_",
        "en": "_· **Player** (Position, Team): Price - **Score**_  \n_(Form: player form, Fixture: match difficulty, Start: probability to start %)_",
    },
    "filters.more": {"es": "Filtros adicionales", "en": "More filters"},
    "filters.complete_more_bold": {"es": "**Filtros adicionales sobre tu lista**", "en": "**Additional filters on your list**"},
    "filters.complete_more": {"es": "Filtros adicionales sobre tu lista", "en": "Additional filters on your list"},
    "filters.fixture": {"es": "Filtrar por dificultad de partido", "en": "Filter by fixture difficulty"},
    "filters.price": {"es": "Filtrar por precio (en M)", "en": "Filter by price (M)"},
    "filters.position": {"es": "**Filtrar por posición:**", "en": "**Filter by position:**"},
    "pos.gk": {"es": "Portero", "en": "Goalkeeper"},
    "pos.def": {"es": "Defensa", "en": "Defender"},
    "pos.mid": {"es": "Mediocentro", "en": "Midfielder"},
    "pos.att": {"es": "Delantero", "en": "Forward"},
    "filters.teams": {"es": "Filtrar por equipos", "en": "Filter by teams"},
    "filters.teams_placeholder": {"es": "Selecciona uno o varios equipos", "en": "Select one or multiple teams"},
    "player.word": {"es": "jugador", "en": "player"},
    "players.word": {"es": "jugadores", "en": "players"},
    "player.found": {"es": "encontrado", "en": "found"},
    "players.found": {"es": "encontrados", "en": "found"},
    "player.filtered": {"es": "filtrado", "en": "filtered"},
    "players.filtered": {"es": "filtrados", "en": "filtered"},
    "player.selected": {"es": "seleccionado", "en": "selected"},
    "players.selected": {"es": "seleccionados", "en": "selected"},
    "btn.copy_players": {"es": "📋 Copiar jugadores", "en": "📋 Copy players"},
    "btn.copy_players_full": {"es": "📋 Copiar jugadores (datos completos)", "en": "📋 Copy players (full data)"},

    # My lineup
    "h.my_best11": {"es": "Selecciona Jugadores para tu 11 ideal", "en": "Select players for your ideal lineup"},
    "cap.add_all": {"es": "Añade a **todos** los jugadores de tu equipo para calcular tu 11 ideal", "en": "Add **all** your squad to compute your best possible lineup"},
    "sb.search_player": {"es": "Buscar jugador", "en": "Search player"},
    "h.selected_players": {"es": "Jugadores seleccionados:", "en": "Selected players:"},
    "cap.lock_note": {
        "es": "_Nota: 'Blindar' jugadores obliga a que estén **sí o sí** en todos los equipos calculados_",
        "en": "_Note: 'Locking' players forces them into all calculated teams_",
    },
    "blind.done": {"es": "🔒 Blindado", "en": "🔒 Locked"},
    "blind.predone": {"es": "Blindar", "en": "Lock"},
    "btn.ready": {"es": "Listo", "en": "Done"},
    "warn.too_strict": {"es": "Filtros demasiado exigentes, selecciona menos filtros.", "en": "Filters too strict, loosen them."},
    "warn.need_11": {"es": "Selecciona al menos 11 jugadores antes de continuar.", "en": "Select at least 11 players before continuing."},
    "h.best_combinations": {"es": "Mejores combinaciones posibles:", "en": "Best possible combinations:"},

    # Market tab
    "h.market": {"es": "Selecciona los Jugadores de tu mercado", "en": "Pick the players from your market"},
    "cap.market": {"es": "Selecciona los Jugadores que han salido en tu mercado para compararlos entre ellos", "en": "Select the players available in your market to compare them"},
    "cap.same_as_list": {"es": "_Nota: es lo mismo que la 'Lista de jugadores', pero seleccionando solo a los jugadores que quieres ver_", "en": "_Note: same as the 'Players list' but only for the players you select_"},
    "players.selected_count": {"es": "{n} {w} seleccionado{s} _({f} filtrado{s})_", "en": "{n} {w} selected _({f} filtered)_"},

    # Tooltips & small texts
    "toast.value_sorted": {"es": "Ordenados de mejor a peor 'chollo'", "en": "Sorted by best 'bargain'"},
    "cap.form_note": {
        "es": "_Nota: ten en cuenta que la 'Forma' se calcula en función de cómo sube o baja el precio del jugador_",
        "en": "_Note: 'Form' is calculated based on the player's price trend_",
    },

    # Footer
    "footer.contact": {"es": "📩 Contacto", "en": "📩 Contact"},

    # Loaders
    "loader.players": {"es": "Cargando jugadores...", "en": "Loading players..."},
    "loader.future_players": {"es": "Cargando jugadores siguiente jornada...", "en": "Loading next weekday players..."},
    "loader.distant_players": {"es": "Cargando jugadores siguientes jornadas...", "en": "Loading next weekdays players..."},
    "loader.knapsack_progress": {
        "es": "Calculando mejores combinaciones",
        "en": "Calculating best combinations"
    },

    # Warnings
    "warning.need": {"es": "Necesitas", "en": "You need"},
    "warning.at_least": {"es": "al menos", "en": "at least"},
    "warning.gk": {"es": "Portero", "en": "Goalkeeper"},
    "warning.gks": {"es": "Porteros", "en": "Goalkeepers"},
    "warning.def": {"es": "Defensa", "en": "Defender"},
    "warning.defs": {"es": "Defensas", "en": "Defenders"},
    "warning.mid": {"es": "Mediocentro", "en": "Midfielder"},
    "warning.mids": {"es": "Mediocentros", "en": "Midfielders"},
    "warning.att": {"es": "Delantero", "en": "Forward"},
    "warning.atts": {"es": "Delanteros", "en": "Forwards"},
    "warning.mas": {"es": " más", "en": ""},
    "warning.more": {"es": "", "en": " more"},

    # Display valid formations
    "formations.name": {"es": "Formación", "en": "Formation"},
    "formations.points": {"es": "puntos", "en": "points"},
    "formations.motivo1": {
      "es": " porque los otros jugadores blindados en esa posición son mejores",
      "en": " because the other locked players in that position are better"
    },
    "formations.motivo2": {
      "es": " con el presupuesto dado",
      "en": " with the given budget"
    },
    "formations.premotivo": {
      "es": "No se pudo incluir a:",
      "en": "Could not include:"
    },
    "formations.see_all": {
      "es": "Ver todos los jugadores utilizados",
      "en": "See all the players used"
    },

    # Print player
    "player.form": {"es": "Forma", "en": "Form"},
    "player.fixture": {"es": "Partido", "en": "Fixture"},
    "player.titular": {"es": "Titular", "en": "Start"},
}

def get_lang():
    # Priority: URL ?lang= -> session_state -> default 'es'
    qp = st.query_params
    if "lang" in qp and qp["lang"] in SUPPORTED_LANGS:
        st.session_state.lang = qp["lang"]
    if "lang" not in st.session_state:
        st.session_state.lang = "es"
    # keep URL in sync for shareable links
    if qp.get("lang") != st.session_state.lang:
        st.query_params.update({"lang": st.session_state.lang})
    return st.session_state.lang

def t(key: str, **kwargs) -> str:
    lang = get_lang()
    txt = I18N.get(key, {}).get(lang, I18N.get(key, {}).get("es", key))
    # allow "{m}" etc
    try:
        return txt.format(**kwargs)
    except Exception:
        return txt

def lang_switcher():
    lang = get_lang()
    label = "Language" if lang == "en" else "Idioma"
    choice = st.sidebar.selectbox(label, options=["es", "en"], format_func=lambda x: "Español" if x=="es" else "English", index=["es","en"].index(lang))
    if choice != lang:
        st.session_state.lang = choice
        st.query_params.update({"lang": choice})
        st.rerun()
# --- end i18n -----------------------------------------------------------------


def sort_players(players, sort_option, use_start_probability=True):
    if sort_option == t("sort.worth"):
        values = [p.value for p in players]
        prices = [p.price for p in players]
        value_ranks_dict = percentile_ranks_dict(values)
        price_ranks_dict = percentile_ranks_dict(prices)
        min_price = min((p.price for p in players if p.price > 0), default=1)
        min_price_percentile = price_ranks_dict.get(0.0, percentile_rank(prices, min_price))
        if use_start_probability:
            return sorted(
                players,
                key=lambda x: (
                    -value_ranks_dict[x.value] * x.start_probability / max(price_ranks_dict[x.price], min_price_percentile),
                    -value_ranks_dict[x.value] / max(price_ranks_dict[x.price], min_price_percentile),
                    -x.start_probability, -x.value, -x.form, -x.fixture, x.price, x.team, x.name
                )
            )
        else:
            return sorted(
                players,
                key=lambda x: (
                    -value_ranks_dict[x.value] / max(price_ranks_dict[x.price], min_price_percentile),
                    x.start_probability, x.value, x.form, x.fixture, x.price, x.team, x.name
                )
            )
    elif sort_option == t("sort.price"):
        return sorted(
            players,
            key=lambda x: (-x.price, -x.value, -x.form, -x.fixture, x.team, x.name)
        )
    elif sort_option == t("sort.form"):
        return sorted(
            players,
            key=lambda x: (-x.form, -x.value, -x.fixture, x.price, x.team, x.name)
        )
    elif sort_option == t("sort.fixture"):
        return sorted(
            players,
            key=lambda x: (-x.fixture, -x.value, -x.form, x.price, x.team, x.name)
        )
    elif sort_option ==t("sort.startprobability"):
        return sorted(
            players,
            key=lambda x: (-x.start_probability, -x.value, -x.form, -x.fixture, x.price, x.team, x.name)
        )
    elif sort_option == t("sort.position"):
        position_priority = {"GK": 0, "DEF": 1, "MID": 2, "ATT": 3}
        return sorted(
            players,
            key=lambda x: (position_priority.get(x.position, 99), -x.value, -x.form, -x.fixture, x.price, x.team, x.name)
        )
    else:  # Puntuación t("sort.score")
        return sorted(
            players,
            key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team, x.name)
        )

def display_valid_formations(formation_score_players_by_score, current_players, blinded_players_names=None, is_biwenger=False):
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

        st.markdown(f"### {t("formations.name")} {formation}: {score:.3f} {t("formations.points")} – 💰 {price}M")
        if missing_ordered:
            # st.warning(f"No se pudo incluir a: {', '.join(missing_ordered)} con el presupuesto dado")
            for missing_player in missing_ordered:
                motivo = ""
                if len(blinded_lines[missing_player.position]) > len(lines[missing_player.position]):
                    motivo = t("formations.motivo1")
                else:
                    motivo = t("formations.motivo2")
                st.warning(f"{t("formations.premotivo")} **{missing_player.name}**{motivo}")

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

        with st.expander(t("formations.see_all")):
            players_show = copy.deepcopy(players)
            for player in players_show:
                blinded_mark = "🔒 " if player.name in blinded_players_names else ""
                # st.markdown(f"- {player} {blinded_mark}")
                player.name = blinded_mark + player.name
                # player.name = player.name + blinded_mark
                print_player(player, small_size=1, is_biwenger=is_biwenger)

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

def print_player(player, small_size=0, is_biwenger=False):
    show_price = player.price / 10 if is_biwenger else player.price
    if small_size==0:
        player_cols = st.columns([12, 1.8, 1, 2, 1, 3])  # Adjust width ratio if needed
        player_cols[0].markdown(
            f"- **{player.name}** ({player.position}, {player.team}): {show_price}M - **{player.value:.3f} pts**"
        )
        player_cols[1].caption(f"{t("player.form")}:")
        player_cols[2].image(player.form_arrow, output_format="PNG", width=24) #, use_container_width=True)
        player_cols[3].caption(f"{t("player.fixture")}:")
        player_cols[4].image(player.fixture_arrow, output_format="PNG", width=24) #, use_container_width=True)
        player_cols[5].markdown(f"{t("player.titular")}: **{player.start_probability*100:.0f} %**")
    elif small_size==1:
        player_cols = st.columns([12, 2.7, 1.5, 3, 1.5, 5])  # Adjust width ratio if needed
        player_cols[0].markdown(
            f"""
                - **{player.name}** ({player.position}, {player.team}):  
                {show_price}M - **{player.value:.3f} pts**
            """
        )
        player_cols[1].markdown("")
        player_cols[1].caption(f"{t("player.form")}:")
        player_cols[2].markdown("")
        player_cols[2].image(player.form_arrow, output_format="PNG", width=24)
        player_cols[3].markdown("")
        player_cols[3].caption(f"{t("player.fixture")}:")
        player_cols[4].markdown("")
        player_cols[4].image(player.fixture_arrow, output_format="PNG", width=24)
        player_cols[5].markdown("")
        player_cols[5].markdown(f"{t("player.titular")}: **{player.start_probability*100:.0f} %**")
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
                {show_price}M - **{player.value:.3f} pts**
            """
        )
        player_cols[2].image(player.form_arrow, output_format="PNG", width=30)#, caption="Forma", use_container_width=True)
        player_cols[2].caption(f"{t("player.form")}")
        player_cols[3].image(player.fixture_arrow, output_format="PNG", width=30)#, caption="Partido", use_container_width=True)
        player_cols[3].caption(f"{t("player.fixture")}")
        player_cols[4].markdown(
            f"""
                {t("player.titular")}:  
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
        player_cols[0].markdown(f"{t("player.titular")}: **{player.start_probability*100:.0f} %**")
        player_cols[1].markdown("")
        player_cols[1].markdown(
            f"""
                **{player.name}** ({player.position}, {player.team}):  
                {show_price}M - **{player.value:.3f} pts**
            """
        )
        player_cols[2].image(player.form_arrow, output_format="PNG", width=30)#, caption="Forma", use_container_width=True)
        player_cols[2].caption(f"{t("player.form")}")
        player_cols[3].image(player.fixture_arrow, output_format="PNG", width=30)#, caption="Partido", use_container_width=True)
        player_cols[3].caption(f"{t("player.fixture")}")
    else:
        player_cols = st.columns([12, 1.8, 1, 2, 1, 3])  # Adjust width ratio if needed
        player_cols[0].markdown(
            f"- **{player.name}** ({player.position}, {player.team}): {show_price}M - **{player.value:.3f} pts**"
        )
        player_cols[1].markdown(f"{t("player.form")}:")
        player_cols[2].image(player.form_arrow, output_format="PNG") #, use_container_width=True)
        player_cols[3].markdown(f"{t("player.fixture")}:")
        player_cols[4].image(player.fixture_arrow, output_format="PNG") #, use_container_width=True)
        player_cols[5].markdown(f"{t("player.titular")}: **{player.start_probability*100:.0f} %**")

def copy_to_clipboard_button(
    text: str,
    label: str = "📋 Copiar",
    key: str = "copy",
    hover_color: str | None = None,
    # hover_color: str | None = "#FF4C4C",
    height: int = 56,
    width_px: int | None = None,
):
    safe_text = json.dumps(text)
    safe_label = html.escape(label)
    btn_id = f"copyBtn-{key}"
    status_id = f"copyStatus-{key}"
    width_style = f"width:{width_px}px;" if width_px else ""

    # Build hover CSS depending on hover_color
    if hover_color is None:
        # No hover/tap color at all
        hover_css = ""
    else:
        # Normalize color: if "", use theme; if "FF4C4C" add "#"
        color = hover_color or (st.get_option("theme.primaryColor") or "#FF4C4C")
        color = color.strip()
        if not color.startswith("#") and not color.startswith("rgb"):
            color = "#" + color

        hover_css = f"""
          #{btn_id}:hover {{
            background:{color};
            border-color:{color};
          }}
          #{btn_id}:focus-visible {{ outline: 2px solid {color}; outline-offset:2px; }}
          /* touch devices don't have hover; give a tap visual */
          @media (pointer:coarse) {{
            #{btn_id}:active {{ background:{color}; border-color:{color}; }}
          }}
        """

    components.html(
        f"""
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
          #{btn_id} {{
            padding:8px 14px; border-radius:10px; border:1px solid #444;
            background:#111; color:#fff; cursor:pointer;
            transition:background .15s ease, border-color .15s ease, transform .06s ease;
            {width_style}
          }}
          #{btn_id}:active {{ transform: scale(0.98); }}
          .status {{ margin-left:8px; font:14px/1.2 sans-serif; }}
          {hover_css}
        </style>

        <div style="display:inline-flex;align-items:center;gap:8px;">
          <button id="{btn_id}" type="button">{safe_label}</button>
          <span id="{status_id}" class="status"></span>
        </div>

        <script>
          const text = {safe_text};

          function legacyCopy(t){{
            const ta=document.createElement('textarea');
            ta.value=t; ta.style.position='fixed'; ta.style.opacity='0';
            document.body.appendChild(ta); ta.focus(); ta.select();
            let ok=false; try{{ ok=document.execCommand('copy'); }}catch(e){{}}
            document.body.removeChild(ta); return ok;
          }}

          const btn=document.getElementById("{btn_id}");
          const statusEl=document.getElementById("{status_id}");
          btn.addEventListener('click', async () => {{
            try {{
              await navigator.clipboard.writeText(text);
              statusEl.textContent="✅ Copiado";
            }} catch(e) {{
              const ok=legacyCopy(text);
              statusEl.textContent = ok ? "✅ Copiado" : "❌ No se pudo copiar";
            }}
            const old=btn.textContent;
            btn.textContent="✅ Copiado";
            setTimeout(()=>{{ btn.textContent=old; statusEl.textContent=""; }}, 1200);
          }});
        </script>
        """,
        height=height,
    )


st.title(t("app.title"))

st.markdown("---")

tab_labels = [
    t("tab.best11_budget"),
    t("tab.my_best11"),
    t("tab.players_list"),
    t("tab.my_market"),
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
lang_switcher()
st.sidebar.header(t("sb.options"))
app_option = st.sidebar.selectbox(t("sb.app"), [t("app.laligafantasy"), t("app.biwenger")], index=1)
penalties_option = st.sidebar.radio(t("sb.penalties"), [t("opt.yes"), t("opt.no")], index=0)
sort_option = st.sidebar.selectbox(t("sb.sort_by"), [t("sort.score"), t("sort.worth"), t("sort.price"), t("sort.form"), t("sort.fixture"), t("sort.startprobability"), t("sort.position")], index=0)
disable_rentabilidad = sort_option != t("sort.worth")
# if disable_rentabilidad:
#     st.sidebar.markdown("<span style='color:gray'>Ordena por 'Rentabilidad' para activar esta opción.</span>", unsafe_allow_html=True)
selected_use_start_probability = st.sidebar.radio(
    t("sb.use_start_prob_with_value"),
    options=[t("opt.yes"), t("opt.no")],
    index=0,
    disabled=disable_rentabilidad
)
use_start_probability = selected_use_start_probability == t("opt.yes")
if sort_option == t("sort.worth"):
    st.toast(t("toast.value_sorted"))
    # use_start_probability = st.sidebar.radio("Utilizar '% Titular' cuando se Ordena por **Rentabilidad**", ["Sí", "No"], index=0)

# Jornada
jornadas_dict = read_dict_data("forced_matches_laliga_2025_26")
display_to_key = {key.replace("_", " ").strip().title().replace("Jornada", t("sb.jornada")): key for key in jornadas_dict}
display_options = [t("jornada.next")] + list(display_to_key.keys())
selected_display_jornada = st.sidebar.selectbox(t("sb.jornada"), options=display_options, format_func=lambda x: normalize_name(x), index=0)
# selected_jornada = [] if selected_display_jornada == "Siguiente partido" else jornadas_dict[display_to_key[selected_display_jornada]]
selected_jornada = jornadas_dict.get(get_next_jornada(), []) if selected_display_jornada == t("jornada.next") else jornadas_dict[display_to_key[selected_display_jornada]]
jornadas_map = {
    t("num.one"): 1,
    t("num.two"): 2,
    t("num.three"): 3,
}
disable_multi_jornada = selected_display_jornada == t("jornada.next")
selected_num_jornadas_label = st.sidebar.selectbox(
    t("sb.num_jornadas"),
    options=list(jornadas_map.keys()),
    format_func=lambda x: normalize_name(x),
    index=0,
    disabled=disable_multi_jornada
)
selected_num_jornadas = jornadas_map[selected_num_jornadas_label]
if disable_multi_jornada:
    st.sidebar.markdown(f"<span style='color:gray'>{t("hint.select_specific_jornada")}</span>", unsafe_allow_html=True)

form_option = st.sidebar.radio(t("sb.ignore_form"), [t("opt.yes"), t("opt.no")], index=1)
fixtures_option = st.sidebar.radio(t("sb.ignore_fixtures"), [t("opt.yes"), t("opt.no")], index=1)

is_biwenger = app_option == t("app.biwenger")
ignore_penalties = penalties_option == t("opt.no")
ignore_form = form_option == t("opt.yes")
ignore_fixtures = fixtures_option == t("opt.yes")

with st.spinner(t("loader.players")):
    current_players = get_current_players(
        no_form=ignore_form,
        no_fixtures=ignore_fixtures,
        no_home_boost=False,
        no_team_history_boost=False,
        alt_fixture_method=False,
        skip_arrows=False,
        use_laligafantasy_data=not is_biwenger,
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
            with st.spinner(t("loader.future_players")):
                future_players = get_current_players(
                    no_form=True,
                    no_fixtures=ignore_fixtures,
                    no_home_boost=False,
                    no_team_history_boost=False,
                    alt_fixture_method=False,
                    use_laligafantasy_data=not is_biwenger,
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
            with st.spinner(t("loader.distant_players")):
                distant_players = get_current_players(
                    no_form=True,
                    no_fixtures=ignore_fixtures,
                    no_home_boost=False,
                    no_team_history_boost=False,
                    alt_fixture_method=False,
                    use_laligafantasy_data=not is_biwenger,
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


# Ocultar el botón de fullscreen de todas las st.image
st.markdown(f"""
    <style>
    div[data-testid="stElementToolbar"] {{
        display: none;
    }}
    </style>
""", unsafe_allow_html=True)

# if main_option == "Mejores 11s con presupuesto" or main_option == "💰 Mejores 11s con presupuesto":
with tabs[0]:
    st.header(t("h.budget11"))

    with st.expander(t("blind.header")):
        current_players_copy = copy.deepcopy(current_players)
        if "blinded_players_set" not in st.session_state:
            st.session_state.blinded_players_set = set()
        if "banned_players_set" not in st.session_state:
            st.session_state.banned_players_set = set()

        st.markdown(f"### {t("blind.title")}")
        st.caption(t("blind.caption1"))
        st.caption(t("blind.caption2"))
        blinded_candidates = [p.name for p in current_players_copy if p.name not in st.session_state.blinded_players_set]
        selected_blindado = st.selectbox(t("blind.add"), options=[""] + blinded_candidates, format_func=lambda x: normalize_name(x), key="add_blindado")
        if selected_blindado:
            st.session_state.blinded_players_set.add(selected_blindado)
            st.session_state.banned_players_set.discard(selected_blindado)
            st.rerun()

        blinded_players_list = [p for p in current_players_copy if p.name in st.session_state.blinded_players_set]
        # Ordenar jugadores
        blinded_players_list = sort_players(blinded_players_list, sort_option, use_start_probability)
        # Mostrar blindados actuales
        for i, p in enumerate(blinded_players_list):
            # cols = st.columns([1, 5, 1])
            # with cols[0]:
            #     st.image(p.img_link, width=60)
            cols = st.columns([9, 1])
            with cols[0]:
                # st.markdown(f"- **{p.name}**: {p.position}, {p.team} – {show_price}M💰 {p.value:.3f} pts --> ({p.start_probability*100:.0f} %)")
                # st.markdown(f"- {p}")
                print_player(p, small_size=3, is_biwenger=is_biwenger)
            with cols[1]:
                if st.button("❌", key=f"remove_blindado_{i}"):
                    st.session_state.blinded_players_set.remove(p.name)
                    blinded_players_list.remove(p)
                    st.rerun()
        if blinded_players_list:
            total_price = sum(p.price / 10 if is_biwenger else p.price for p in blinded_players_list)
            st.caption(f"{t("blind.total_price")} **{total_price}M**")

        st.markdown(f"### {t("ban.title")}")
        st.caption(t("ban.caption"))
        banned_candidates = [p.name for p in current_players_copy if p.name not in st.session_state.banned_players_set]
        selected_baneado = st.selectbox(t("ban.add"), options=[""] + banned_candidates, format_func=lambda x: normalize_name(x), key="add_baneado")
        if selected_baneado:
            st.session_state.banned_players_set.add(selected_baneado)
            st.session_state.blinded_players_set.discard(selected_baneado)
            st.rerun()

        banned_players_list = [p for p in current_players_copy if p.name in st.session_state.banned_players_set]
        # Ordenar jugadores
        banned_players_list = sort_players(banned_players_list, sort_option, use_start_probability)
        # Mostrar baneados actuales
        for i, p in enumerate(banned_players_list):
            # cols = st.columns([1, 5, 1])
            # with cols[0]:
            #     st.image(p.img_link, width=60)
            cols = st.columns([9, 1])
            with cols[0]:
                # st.markdown(f"- **{p.name}**: {p.position}, {p.team} – {show_price}M💰 {p.value:.3f} pts --> ({p.start_probability*100:.0f} %)")
                # st.markdown(f"- {p}")
                print_player(p, small_size=1, is_biwenger=is_biwenger)
            with cols[1]:
                if st.button("❌", key=f"remove_baneado_{i}"):
                    st.session_state.banned_players_set.remove(p.name)
                    banned_players_list.remove(p)
                    st.rerun()

    if is_biwenger:
        budget = st.number_input(t("sb.budget.max"), min_value=-1.0, max_value=100.0, value=30.0, step=0.1, key="budget_cap", format="%.1f")
        budget = int(budget * 10)
    else:
        budget = st.number_input(t("sb.budget.max"), min_value=-1, max_value=1000, value=200, step=1, key="budget_cap")
    st.caption(t("sb.budget.hint"))
    # if is_biwenger:
    #     st.markdown(f"En Biwenger: **{budget / 10:.1f}M**")

    with st.expander(t("sb.extra_filters"), expanded=True):
        use_fixture_filter = st.radio(
            t("sb.exclude_hard_fixtures"), [t("opt.no"), t("opt.yes")], index=0 if is_biwenger else 1,key="fixture_filter_budget"
        ) == t("opt.yes")
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 65, key="prob_threshold_budget")
        # threshold = threshold_slider / 100
        prob_key = "prob_threshold_budget"
        min_prob_slider, max_prob_slider = st.slider(t("sb.start_prob_range"), 0, 100, (65, 100), key=prob_key)
        max_prob_slider = 100
        # Ocultar el segundo handle (derecho) del slider
        st.markdown(f"""
            <style>
            div[class*="st-key-{prob_key}"] div[data-baseweb="slider"] div[role="slider"]:nth-child(2) {{
                display: none;
            }}
            </style>
        """, unsafe_allow_html=True)
        min_prob = min_prob_slider / 100
        max_prob = max_prob_slider / 100

        use_slow_calc = st.checkbox(t("sb.slow_calc"), value=False, key="is_slow_calc")
        st.caption(t("sb.slow_calc_hint"))

    use_premium = st.checkbox(t("sb.premium_formations"), value=False, key="premium_budget")

    my_filtered_players = purge_everything(
        current_players_copy,
        probability_threshold=min_prob,
        fixture_filter=use_fixture_filter
    )
    my_filtered_players_names = [p.name for p in my_filtered_players]
    my_filtered_players = [
        p for p in current_players_copy
        if p.name not in st.session_state.banned_players_set and (
                (p.name in my_filtered_players_names and min_prob <= p.start_probability <= max_prob)
                or p.name in st.session_state.blinded_players_set
        )
    ]

    for player in my_filtered_players:
        if player.name in st.session_state.blinded_players_set:
            # player.price = 0
            player.value = max(1000, player.value*1000)
            player.start_probability = 10
            player.form = 10
            player.fixture = 10

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

    if st.button(t("btn.calc11"), key="submit_budget_11") and my_filtered_players:
        st.markdown(f"## {t("h.best_combinations_budget")}")
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
            speed_up=not use_slow_calc,
            translator=t,
            verbose=2,
        )

        display_valid_formations(formation_score_players_by_score, current_players, st.session_state.blinded_players_set, is_biwenger)

# Funcionalidades futuras
# elif main_option == "Mi mejor 11 posible" or main_option == "⚽ Mi mejor 11 posible":
with tabs[1]:
    st.header(t("h.my_best11"))
    st.caption(t("cap.add_all"))

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
    selected_name = st.selectbox(t("sb.search_player"), options=[""] + player_names, format_func=lambda x: normalize_name(x), key="busca_jugador")
    if selected_name not in st.session_state.my_players_names:
        st.session_state.my_players_names.add(selected_name)
        st.rerun()

    # Reconstruir lista de objetos player
    current_players_copy = copy.deepcopy(current_players)
    my_players_list = [p for p in current_players_copy if p.name in st.session_state.my_players_names]

    # Mostrar jugadores seleccionados
    if my_players_list:
        st.markdown(f"### {t("h.selected_players")}")
        st.caption(t("cap.lock_note"))
        # Ordenar jugadores
        my_players_list = sort_players(my_players_list, sort_option, use_start_probability)
        my_players_list_show = copy.deepcopy(my_players_list)
        for i, p in enumerate(my_players_list_show):
            cols = st.columns([8, 1, 2])
            # with cols[0]:
            #     st.image(p.img_link, width=70)
            with cols[0]:
                # st.markdown(f"**{p.name}** - {p.position} - {p.team} - {p.price}M - {p.value} pts")
                # st.markdown(f"{p}")
                print_player(p, small_size=3, is_biwenger=is_biwenger)
            with cols[1]:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.my_players_names.remove(p.name)
                    st.session_state.blinded_players.discard(p.name)
                    st.rerun()
            with cols[2]:
                is_blinded = p.name in st.session_state.blinded_players
                blindar_label = t("blind.done") if is_blinded else t("blind.predone")
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
    with st.expander(t("filters.complete_more_bold"), expanded=True if my_players_list else 0):
        use_fixture_filter = st.radio(
            t("sb.exclude_hard_fixtures"), [t("opt.no"), t("opt.yes")], index=0 if is_biwenger else 1,key="fixture_filter_my11"
        ) == t("opt.yes")
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 65, key="prob_threshold_my11")
        # threshold = threshold_slider / 100
        prob_key = "prob_threshold_my11"
        min_prob_slider, max_prob_slider = st.slider(t("sb.start_prob_range"), 0, 100, (65, 100), key=prob_key)
        max_prob_slider = 100
        # Ocultar el segundo handle (derecho) del slider
        st.markdown(f"""
            <style>
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
    use_premium = st.checkbox(t("sb.premium_formations"), value=False)

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
    if st.button(t("btn.ready"), key="submit_my_11") and filtered_players:
        counts = Counter(player.position for player in filtered_players)
        position_counts = {pos: counts.get(pos, 0) for pos in ["GK", "DEF", "MID", "ATT"]}
        if use_premium:
            if position_counts["GK"] < 1:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 1 {t("warning.gk")}.")
            if position_counts["DEF"] < 3:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 3 {t("warning.defs")}.")
            if position_counts["MID"] < 2:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 2 {t("warning.mids")}.")
            if position_counts["ATT"] < 0:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 0 {t("warning.atts")}.")
            if position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 5{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 4:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.def")}/{t("warning.mid")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 6 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.def")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 4 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 2 and position_counts["ATT"] == 2:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 5 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 3:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.def")}/{t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 5 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.def")}/{t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 3:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 5 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 3 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 2 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 2:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 4 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 2:
                st.warning(f"{t("warning.need")} 3{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 4 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 3{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 2 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 3{t("warning.more")} {t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 4 and position_counts["MID"] == 3 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 3{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 3{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 2 and position_counts["ATT"] >= 1:
                st.warning(f"{t("warning.need")} 4{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 3 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 4{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 2 and position_counts["ATT"] == 0:
                st.warning(f"{t("warning.need")} 4{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            # else:
            #     if position_counts["GK"] >= 1 and position_counts["DEF"] >= 3 and position_counts["MID"] >= 2 and position_counts["ATT"] >= 0:
            #         st.warning("Necesitas al menos 1 Defensa/Mediocentro/Delantero más")
            #         st.warning(f"{t("warning.need")} {t("warning.at_least")} 1{t("warning.more")} {t("warning.def")}/{t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
        else:
            if position_counts["GK"] < 1:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 1 {t("warning.gk")}.")
            if position_counts["DEF"] < 3:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 3 {t("warning.defs")}.")
            if position_counts["MID"] < 3:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 3 {t("warning.mids")}.")
            if position_counts["ATT"] < 1:
                st.warning(f"{t("warning.need")} {t("warning.at_least")} 1 {t("warning.att")}.")
            if position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 3{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 3:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.def")}/{t("warning.mid")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 5 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.def")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 5 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 1{t("warning.more")} {t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] == 3 and position_counts["ATT"] >= 2:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] == 3 and position_counts["MID"] >= 4 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            elif position_counts["GK"] >= 1 and position_counts["DEF"] >= 4 and position_counts["MID"] == 3 and position_counts["ATT"] == 1:
                st.warning(f"{t("warning.need")} 2{t("warning.more")} {t("warning.defs")}/{t("warning.mids")}/{t("warning.atts")}{t("warning.mas")}")
            # else:
            #     if position_counts["GK"] >= 1 and position_counts["DEF"] >= 3 and position_counts["MID"] >= 3 and position_counts["ATT"] >= 1:
            #         st.warning("Necesitas al menos 1 Defensa/Mediocentro/Delantero más")
            #         st.warning(f"{t("warning.need")} {t("warning.at_least")} 1 {t("warning.def")}/{t("warning.mid")}/{t("warning.att")}{t("warning.mas")}")
        if len(filtered_players) < 11:
            if len(my_players_list) >= 11:
                st.warning(t("warn.too_strict"))
            else:
                st.warning(t("warn.need_11"))
        else:
            st.markdown(f"## {t("h.best_combinations")}")
            worthy_players = sorted(
                filtered_players,
                key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team),
                reverse=False
            )
            formation_score_players_by_score = best_full_teams(
                worthy_players,
                possible_formations,
                -1,
                translator=t,
                verbose=1
            )
            # print_best_full_teams(formation_score_players_by_score)
            display_valid_formations(formation_score_players_by_score, current_players, st.session_state.blinded_players, is_biwenger)

# Si selecciona "Lista de jugadores"
# ekif main_option == "Lista de jugadores" or main_option == "📋 Lista de jugadores":
with tabs[2]:
    st.header(t("h.players_list"))
    st.markdown(t("players.legend"))

    # Filtros adicionales
    with st.expander(t("filters.more")):
        use_fixture_filter = st.radio(t("filters.fixture"), [t("opt.no"), t("opt.yes")], index=0) == t("opt.yes")
        # threshold_slider = st.slider("Probabilidad mínima de titularidad (%)", 0, 100, 0)
        # threshold = threshold_slider / 100

        prob_key = "prob_threshold_playerslist"
        # if prob_key in st.session_state:
        #     min_val = st.session_state[prob_key][0]
        #     st.session_state[prob_key] = (min_val, 100)
        # else:
        #     st.session_state[prob_key] = (0, 100)
        # min_prob_slider, max_prob_slider = st.slider("Probabilidad de ser titular (%)", 0, 100, value=st.session_state[prob_key], key=prob_key)
        min_prob_slider, max_prob_slider = st.slider(t("sb.start_prob_range"), 0, 100, (0, 100), key=prob_key)
        max_prob_slider = 100
            # div[class*="st-key-prob_threshold_playerslist"] div[data-testid="stSlider"] > div > div > div > div:nth-child(2) {
            # div[class*="st-key-prob_threshold_playerslist"] div > div > div > div > div > div:nth-child(2) {
        # Ocultar el segundo handle (derecho) del slider
        st.markdown(f"""
            <style>
            div[class*="st-key-{prob_key}"] div[data-baseweb="slider"] div[role="slider"]:nth-child(2) {{
                display: none;
            }}
            </style>
        """, unsafe_allow_html=True)
        min_prob = min_prob_slider / 100
        max_prob = max_prob_slider / 100

        # Filtro por precio
        max_player_price = max((p.price for p in current_players), default=300)
        if is_biwenger:
            max_player_price_show = round(max_player_price / 10, 1)
            min_price, max_price = st.slider(t("filters.price"), 0.0, max_player_price_show, (0.0, max_player_price_show), step=0.1, key="slider_precio", format="%.1f")
            min_price = int(round(min_price * 10))
            max_price = int(round(max_price * 10))
        else:
            max_player_price_show = max_player_price
            min_price, max_price = st.slider(t("filters.price"), 0, max_player_price, (0, max_player_price), step=1, key="slider_precio", format="%.0f")

        # Filtro por posición
        st.markdown(t("filters.position"))
        filter_gk = st.checkbox(t("pos.gk"), value=True)
        filter_def = st.checkbox(t("pos.def"), value=True)
        filter_mid = st.checkbox(t("pos.mid"), value=True)
        filter_att = st.checkbox(t("pos.att"), value=True)

        filter_teams = st.multiselect(t("filters.teams"), options=current_team_list, format_func=lambda x: normalize_name(x), placeholder=t("filters.teams_placeholder"))

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
    current_players_filtered = sort_players(current_players_filtered, sort_option, use_start_probability)

    # Mostrar resultados
    num_jugadores = len(current_players_filtered)
    jugador_texto = t("player.word") if num_jugadores == 1 else t("players.word")
    encontrado_texto = t("player.found") if num_jugadores == 1 else t("players.found")
    st.subheader(
        f"{num_jugadores} {jugador_texto} {encontrado_texto}"
    )

    show_players = copy.deepcopy(current_players_filtered)
    for player in show_players:
        # st.text(str(player))
        print_player(player, small_size=0, is_biwenger=is_biwenger)

    copiable_text = "\n".join(f"- {p.name}" for p in show_players)
    copiable_full_text = "\n".join(f"- {p}" for p in show_players)

    cols = st.columns([5, 10, 1, ])
    with cols[0]:
        copy_to_clipboard_button(copiable_text, label=t("btn.copy_players"), key="players", )
    with cols[1]:
        copy_to_clipboard_button(copiable_full_text, label=t("btn.copy_players_full"), key="players_full", )

with tabs[3]:
    st.header(t("h.market"))
    st.caption(t("cap.market"))
    st.caption(t("cap.same_as_list"))

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
    selected_name = st.selectbox(t("sb.search_player"), options=[""] + player_names, format_func=lambda x: normalize_name(x), key="busca_mercado")
    if selected_name not in st.session_state.my_players_names_set:
        st.session_state.my_players_names_set.add(selected_name)
        st.rerun()

    # Reconstruir lista de objetos player
    current_players_copy = copy.deepcopy(current_players)
    my_market_players_list = [p for p in current_players_copy if p.name in st.session_state.my_players_names_set]

    # Mostrar jugadores seleccionados
    if my_market_players_list:
        # Filtros adicionales aplicados sobre `my_market_players_list`
        with st.expander(t("filters.complete_more")):
            use_fixture_filter = st.radio(t("filters.fixture"), [t("opt.no"), t("opt.yes")], index=0, key="fixture_filter") == t("opt.yes")
            prob_key = "prob_threshold_marketplayerslist"
            min_prob_slider, max_prob_slider = st.slider(t("sb.start_prob_range"), 0, 100, (0, 100), key=prob_key)
            max_prob_slider = 100
            # Ocultar el segundo handle (derecho) del slider
            st.markdown(f"""
                <style>
                div[class*="st-key-{prob_key}"] div[data-baseweb="slider"] div[role="slider"]:nth-child(2) {{
                    display: none;
                }}
                </style>
            """, unsafe_allow_html=True)
            min_prob = min_prob_slider / 100
            max_prob = max_prob_slider / 100

            # Filtro por precio
            max_player_price = max((p.price for p in current_players), default=300)
            if is_biwenger:
                max_player_price_show = round(max_player_price / 10, 1)
                min_price, max_price = st.slider(t("filters.price"), 0.0, max_player_price_show, (0.0, max_player_price_show), step=0.1, key="slider_precio_market", format="%.1f")
                min_price = int(round(min_price * 10))
                max_price = int(round(max_price * 10))
            else:
                max_player_price_show = max_player_price
                min_price, max_price = st.slider(t("filters.price"), 0, max_player_price, (0, max_player_price), step=1, key="slider_precio_market", format="%.0f")

            # Filtro por posición
            st.markdown(t("filters.position"))
            filter_gk = st.checkbox(t("pos.gk"), value=True, key="filter_gk")
            filter_def = st.checkbox(t("pos.def"), value=True, key="filter_def")
            filter_mid = st.checkbox(t("pos.mid"), value=True, key="filter_mid")
            filter_att = st.checkbox(t("pos.att"), value=True, key="filter_att")

            filter_teams = st.multiselect(t("filters.teams"), options=current_team_list, format_func=lambda x: normalize_name(x), placeholder=t("filters.teams_placeholder"), key="multichoice_teams")

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
        jugador_texto = t("player.word") if num_jugadores == 1 else t("players.word")
        filtrado_texto = t("player.filtered") if num_filtrados == 1 else t("players.filtered")
        seleccionado_texto = t("player.selected") if num_jugadores == 1 else t("players.selected")
        st.subheader(
            f"{num_jugadores} {jugador_texto} {seleccionado_texto}" + f" _({num_filtrados} {filtrado_texto})_"
        )
        st.caption(t("cap.form_note"))

        # Ordenar jugadores
        my_market_filtered_players_list = sort_players(my_market_filtered_players_list, sort_option, use_start_probability)
        my_market_filtered_players_list_show = copy.deepcopy(my_market_filtered_players_list)
        for i, p in enumerate(my_market_filtered_players_list_show):
            cols = st.columns([9, 1])
            # with cols[0]:
            #     st.image(p.img_link, width=60)
            with cols[0]:
                # st.markdown(f"**{p.name}** - {p.position} - {p.team} - {p.price}M - {p.value} pts")
                # st.markdown(f"{p}")
                print_player(p, small_size=1, is_biwenger=is_biwenger)
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
st.markdown(f"{t("footer.contact")}: [calculadora.fantasy@gmail.com](mailto:calculadora.fantasy@gmail.com)")

# Auto-update trigger: Fri Sep  5 00:14:55 UTC 2025
