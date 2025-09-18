import ast
import json
import os
import shutil

import requests
import tls_requests
import urllib3
from bs4 import BeautifulSoup
from unidecode import unidecode
import difflib
from fuzzywuzzy import fuzz
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import concurrent.futures
import stopit
import numpy as np

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


def cleaned_string(s):
    res = s
    return unidecode(str(res)).lower().replace(" ", "").replace("-", "")

def format_string(s):
    words = s.split()
    if len(words) > 1:
        return words[0][0] + '. ' + ' '.join(words[1:])
    return s


def find_similar_string(my_string, string_list, similarity_threshold=0.8, verbose=False, is_formatted=False, fallback_none=False):
    if my_string in ["Álvaro Carreras", "Álvaro Fernández", "Á. Fernandez", "Pape Matar Sarr", "Pape Sarr", "Frank Anguissa", ]:
        similarity_threshold = 0.65
    # Before anything, we check the manual checks
    if not is_formatted:
        my_manual_string = find_manual_similar_string(my_string, fallback_none=fallback_none)
        if (not fallback_none and my_manual_string != my_string) or (fallback_none and my_manual_string is not None): # If it found something
            return my_manual_string
    # First, check for '==' in the list
    if my_string in string_list:
        # if verbose:
        #     print(f"Most similar string for \"{my_string}\": {my_string} (100 %)")
        return my_string
    my_string_clean = cleaned_string(my_string)
    # Second, check for exact equality after cleaning
    for list_string in string_list:
        list_string_clean = cleaned_string(list_string)
        if my_string_clean == list_string_clean:
            # if verbose:
            #     print(f"Most similar string for \"{my_string}\": {my_string_clean} (~100 %)")
            return list_string
    # Third, check for partial match after cleaning
    for list_string in string_list:
        list_string_clean = cleaned_string(list_string)
        if my_string_clean in list_string_clean or list_string_clean in my_string_clean:
            # if verbose:
            #     print(f"Most similar string for \"{my_string}\": {list_string_clean} (~100 %)")
            return list_string
    # Fourth, the initial checks, apply the special formatting (point rule) and check again, but only once
    if not is_formatted and ' ' in my_string:  # Check if my_string contains more than one word and hasn't been formatted
        formatted_string = format_string(my_string)
        result = find_similar_string(formatted_string, string_list, similarity_threshold=1, verbose=False, is_formatted=True)
        if result:
            return result
        # Do the point rule with the string from the other side
        formatted_dict = {format_string(item): item for item in string_list}
        formatted_string_list = list(formatted_dict.keys())
        result = find_similar_string(my_string, formatted_string_list, similarity_threshold=1, verbose=False, is_formatted=True)
        if result:
            return formatted_dict[result]
    # Lastly, check for the most similar string
    max_similarity = 0
    most_similar_string = None
    for list_string in string_list:
        s = difflib.SequenceMatcher(None, my_string_clean, cleaned_string(list_string))
        similarity = s.ratio()
        # similarity = fuzz.ratio(my_string_clean, cleaned_string(list_string))/100
        if similarity > max_similarity:
            max_similarity = similarity
            most_similar_string = list_string
    if verbose:
    # if True:
        print(f"Most similar string for \"{my_string}\": {most_similar_string} ({max_similarity*100:.2f} %)")
    if max_similarity >= similarity_threshold:
        # print("ENTRA")
        # print(string_list)
        return most_similar_string
    return None


def find_manual_similar_string(my_string, fallback_none=False):
    normalization_dict = {
        "Alfonso Espino": "Pacha Espino",
        "Abderrahman Rebbach": "Abde Rebbach",
        "Peter González": "Peter Federico",
        "Peter Gonzales": "Peter Federico",
        "Abde Ezzalzouli": "Ez Abde",
        "Abdessamad Ezzalzouli": "Ez Abde",
        "Chuky": "Chuki",
        "Malcom Ares": "Adu Ares",
        "William Carvalho": "Carvalho",
        "Fabio González": "Fabio",
        "Jonathan Montiel": "Joni Montiel",
        "Jon Magunazelaia": "Magunacelaya",
        "Álvaro Aguado": "Aguado",
        "Isco Alarcon": "Isco",
        "Isco Alarcón": "Isco",
        "Fabio Gonzalez": "Fabio",
        "Fabio Silva": "Fábio Silva",
        "Coba da Costa": "Coba Gomes",
        "Jose Maria Gimenez": "Giménez",
        "José María Giménez": "Giménez",
        "Julián A.": "Julián Alvarez",
        "Dani R.": "Dani Rodríguez",
        "Nahuel": "Molina",
        # "Miguel": "De La Fuente",
        "Antonio S.": "Antonio Sánchez",
        "Aritz": "Elustondo",
        "De Zárate": "Urko Gonzalez",
        "Aitor Fdez.": "Aitor Fernández",
        "Adama": "Boiro",
        # "Rdt": "De Tomás",
        "Sergi D.": "Sergi Domínguez",
        "Franco": "Mastantuono",
        "Franco Mastantuono": "Mastantuono",
        "Pablo Cuñat": "Pablo Campos",
        "Jonny Otto": "Jonny Castro",
        "Unai Elguezabal": "Elgezabal",
        "Unai Eguíluz": "Egiluz",
        "Abdel Rahim": "Alhassane",
        "H. Hassan": "Alhassane",
        "Rahim": "Alhassane",
        "A. Rahim": "Alhassane",
        "Ismaila Ciss": "Pathé Ciss",
        "Pathé Ismaël Ciss": "Pathé Ciss",
        "Pathé I. Ciss": "Pathé Ciss",
        "John Nwankwo": "John Donald",
        "John C.": "John Donald",
        "Nicolás Fernández Mercau": "Nico Fernández",
        "Carlos Protesoni": "Benavidez",
        "Protesoni": "Benavidez",
        "E. Etoo": "Etienne Eto'o",
        "Yeremi": "Yéremy Pino",
        "Yeremy": "Yéremy Pino",
        "Yéremi": "Yéremy Pino",
        "Yéremy": "Yéremy Pino",
        "Haissem Hassan": "Hassan",
        "Andrei": "Ratiu",
        "Carlos V.": "Carlos Vicente",
        "Vini Jr.": "Vinícius Jr",
        "Cenk": "Özkacar",
        "Júnior R.": "Luiz Júnior",
        "Mateu Jaume": "Mateu Morey",
        "S. C. Tenés": "Sergi Canós",
        "Williot": "Swedberg",
        "Aarón": "Escandell",
        "Aitor Fdez": "Aitor Fernández",
        "Mouriño": "Santiago Mouriño",
        "Unai G.": "Unai Gómez",
        "Maroan": "Sannadi",
        "Carlos M.": "Carlos Martín",
        "Mourad": "El Ghezouani",
        "Rubén S.": "Rubén Sánchez",
        "Areso": "Areso",
        "Olasagasti": "Olasagasti",
        "Pablo Gavi": "Gavi",
        "Alejandro Primo": "Álex Primo",

        "Khéphren Thuram": "K. Thuram-Ulien",
        "Thuram-Ulien": "K. Thuram-Ulien",
        "Khéphren Thuram-Ulien": "K. Thuram-Ulien",
        "Khephren Thuram": "K. Thuram-Ulien",
        # "K. Thuram": "K. Thuram-Ulien",
        "Samuel Aghehowa": "Samu Omorodion",
        "Samu Aghehowa": "Samu Omorodion",
        "Stiven Barreiro": "Jaine Barreiro",
        "Nene Dorgeles": "Dorgeles Nene",
        "Kodjo Fo Doh Laba": "Kodjo Laba",
        "Danny Namaso": "Danny Loader",
        "Moussa Kounfolo Yeo": "Boiro",
        "Jeremías Ledesma": "Conan Ledesma",
        "Alejandro Romero": "Kaku",
        "El Mehdi Benabid": "E. Benabid",
        "Jeong-in Mun": "Jung-in Moon",
        "Hamad Al Yami": "M. Al-Yami",
        "Mostafa Shobeir": "Oufa Shobeir",
        "Mohamed Sedki Debchi": "M. Debchi",
        "Kouame Autonne Kouadio": "K. Kouadio",
        "Amine Ben Hamida": "M. Ben Hamida",
        "Mohamed Amine Ben Hamida": "M. Ben Hamida",
        "Ahmed Nabil Koka": "Ahmed Kouka",
        "Daniel Aceves": "Alonso Aceves",
        "Bandar Al Ahbabi": "Bandar Mohamed",
        "Jonathan Bell": "Jon Bell",
        "Jong-kyu Yun": "Jong-gyu Yoon",
        "Ahmed Hashem": "Ahmed Reda",
        "Kutlwano Letlhaku": "K. Lethlaku",
        "Khalid Al Zaabi": "Khalid Butti",
        "Mohamed Wael Derbali": "M. Derbali",
        "David Seung Ho Yoo": "David Yoo",
        "Jaeik Lee": "Jae-wook Lee",
        "Mouad Aounzou": "Mouad Enzo",
        "Pedro Jair Ramírez Orta": "Pedro Ramírez",
        "Jang Si-young": "See-young Jang",
        "Mohamed Rayane Hamrouni": "M. Hamrouni",
        "José Manuel López": "José López",
        "Erling Braut Haland": "Haaland",
        "Kim Min-Jae": "Min-jae Kim",
        "Mohamed Amine Tougai": "M. Tougai",
        "Kim Young-Gwon": "Young-gwon Kim",
        "Jung Woo-Young": "Woo-young Jung",
        "Lee Chung-Yong": "Chung-yong Lee",
        "Rodri Hernandez": "Rodrigo",
        "Rodri Heráandez": "Rodrigo",
        "R. Rabia": "Rami Rabia",
        "Mohamed Ali Ben Romdhane": "M. Ben Romdhane",
        "Arnold": "Trent Alexander-Arnold",
        "T. Alexander-Arnold": "Trent Alexander-Arnold",
        # "Trent Alexander-Arnold": "Trent",
        # "Trent": "Trent Alexander-Arnold",
        "B. Said": "Bechir Ben Said",
        "W. Ali": "Wessam Abou Ali",
        "K. Debes": "Karim El Debes",
        "M. Aash": "Mostafa El Aash",
        "D. Vega": "De la Vega",
        "Marwan Attia": "Ateya",
        "Gonzalo Martinez": "Pity Martínez",
        "Artem Smoliakov": "Smolyakov",
        "Youssef Lekhedim": "Yusi Enríquez",
        "Youssef Enríquez": "Yusi Enríquez",
        "Abdulaziz Hadhood": "Al-Hadhood",
        "Saad Al Muthary": "Al-Mutairi",
        "Saad Khalid Almuthary": "Al-Mutairi",
        "Saad Al-Muthary": "Al-Mutairi",
        "El Hadji Malick Diouf": "El Diouf",
        "Ajibola-Joshua Alese": "Aji Alese",
        "Ian Carlo Poveda": "Ian Poveda",
        # "Pape Matar Sarr": "Pape Sarr",
        "Jorgen Strand Larsen": "Larsen",
        "V. Ven": "Van de Ven",
        "Reinildo": "Mandava",
        "Yehor Yarmoliuk": "Yarmolyuk",
        "Gabriel": "Magalhães",
        "Raya Martin": "David Raya",
        "Tosin": "Adarabioyo",
        "Bruun Larsen": "Jacob Larsen",
        "Valentín Castellanos": "Taty Castellanos",
        # "Frank Anguissa": "Zambo Anguissa",
        "Andre Zambo Anguissa": "Zambo Anguissa",
        "Vakoun Issouf Bayo": "Vakoun Bayo",
        "Jean-Daniel Akpa Akpro": "Akpa Akpro",
        "Jeremy Kandje Mbambi": "Jeremy Mbambi",
        "Marc-Oliver Kempf": "Marc Kempf",
        "Hans Nicolussi Caviglia": "Hans Caviglia",
        "Mathias Fjørtoft Løvik": "Mathias Løvik",
        "Nicolas-Gerrit Kühn": "Nicolas Kühn",
        "Cheick Tidiane Sabaly": "Cheick Sabaly",
        "Matias Fernandez": "Fernandez-Pardo",
        "Serigne Diop": "Saliou Diop",
        "Michel Diaz": "Junior Diaz",
        "Christian Mawissa": "Mawissa Elebi",
        "Kelvin Amian": "Amian Adou",
        "Samir Sophian Chergui": "Samir Chergui",
        "Gaëtan Bakhouche": "Bakhouche Piernas",
        "Joel Mugisha Mvuka": "Joel Mvuka",
        "Oualid El Hajjam": "El Hajam",
        "Marius Sivertsen Broholm": "Marius Broholm",
        "Conrad Jaden Egan-Riley": "CJ Egan-Riley",
        "Junior Dina Ebimbe": "Eric Ebimbe",
        "Moustapha Mbow": "Mamadou Mbow",
        "Karim Dermane": "Dermane Karim",
        "Hamed Junior Traorè": "Hamed Traoré",
        "Lionel M'Pasi": "Mpasi",
        # "Kevin Medina": "Kevin Medina Villodres",
        "Kevin David Medina Renteria": "Kevin Medina Villodres",
        "Kevin Villodres": "Kevin Medina Villodres",
        "Fernando Niño": "Fer Niño",
        "Samuel Obeng": "Samuel Gyabaa",
        "Kialy Abdoul Kone": "Kialy Kone",
        "Manuel Lama Maroto": "Manu Lama",
        "Rodrigo Abajas": "Ro Abajas",
        "Alberto Rodríguez": "Tachi",
        "José Carlos Lazo": "José Lazo",
        "Christian Sanchez": "Joel Sanchez",
        "Marcos André": "Marcos de Sousa",
        "José Manuel Arnáiz": "José Arnaiz",
        "Álex Cardero": "Álex Suárez",
        "Franco Santi": "Santi Franco",
        "D. Fuente": "De La Fuente",
        "L. León": "Lautaro de León",
        "Guilherme Guedes": "Gui Guedes",
        # "Álvaro Carreras": "Álvaro Carreras Fernández",
        "Carreras": "Álvaro Carreras",
        "Álvaro F. Carreras": "Álvaro Carreras",
        "Á. Carreras": "Álvaro Carreras",
        "Alvaro Carreras": "Álvaro Carreras",
        "Á. F. Carreras": "Álvaro Carreras",
        "Álvaro Carreras Fernández": "Álvaro Carreras",
        "Alejandro Baena": "Álex Baena",
        "David Datro Fofana": "David Fofana",
        "Georgiy Sudakov": "Heorhii Sudakov",
        "Neofytos Michael": "N. Michail",
        "Oscar Gadeberg Buur": "Oscar Buur",
        "Luis Javier Suárez": "Luis Suárez",
        "Luis Javier Suarez": "Luis Suárez",
        "Leandro Barreiro": "Barreiro Martins",
        "Kaye Iyowuna Furo": "Kaye Furo",
        "Julian Faye Lund": "J. Lund",
        "Isak Dybvik Määttä": "I. Määttä",
        "Rúnar Alex Rúnarsson": "R. Rúnarsson",
        "Şahrudin Mahammadaliev": "S. Mahammadaliyev",
        "Bədavi Hüseynov": "Guseynov",
        "Chris Kouakou": "Chriso",
        "Arad Ofri": "Ofri Arad",
        "Mads Emil Madsen": "M. Madsen",
        "Jens Petter Hauge": "J. Hauge",
        "Ole Didrik Blomberg": "O. Blomberg",
        "Nariman Akhundzade": "N. Akhundzada",
        "Maximiliano Araújo": "Maxi Araújo",
        "Viktor Gyoekeres": "Gyökeres",
        "Kady Malinowski": "Kady Borges",
        "Bahlul Mustafazade": "B. Mustafazada",
        "Elvin Jafarquliyev": "E. Cafarquliyev",
        "Francisco Gabriel Ortega": "F. Ortega",
        "Álex Grimaldo": "Alejandro Grimaldo",
        "G. Borges Guedes": "Gui Guedes",
        "F. Jesús Crespo": "Pejiño",
        "I. S. Magaña": "Piña",
        "A. C. Armendariz": "Ander Cantero",
        "J. Luis Kuki": "Kuki Zalazar",
        "Juan Ferney Otero": "Juan Otero",
        "Campos Gaspar": "Gaspar Campos",
        "Pau de la Fuente": "Paulino",
        "F. Javier Montero": "Francisco Montero",
        "A. Ndiaye Diedhiou": "Amath",
        "Marcos Andre": "Marcos de Sousa",
        "E. Hadji Malick": "El Diouf",
        "Marc Oliver Kempf": "Marc Kempf",
        "M. Fjörtoft Lövik": "Mathias Løvik",
        "M. Egill Ellertsson": "Mikael Ellertsson",
        "A. Matheus dos": "Antony",
        "J. Manuel Arias": "Copete",
        "A. D. Groeneveld": "Danjuma",
        "Vini Jr": "Vinícius Jr",
        "Karl Etta": "Etta Eyong",
        "Andrei Radu": "Ionut Radu",
        "Aaron": "Escandell",
        "Tolu": "Arokodare",
        "Mbwana Samatta": "Ally Samatta",
        "Koffi Franck Kouao": "Koffi Kouao",
        "Kevin Omoruyi": "Kevin Carlos",
        "Eric Junior": "Eric Ebimbe",
        "AAAAAAAA": "BBBBBBB",
        "AAAAAAAA": "BBBBBBB",
        "AAAAAAAA": "BBBBBBB",

        "RCD Espanyol Barcelona": "Espanyol",
        "RCD Espanyol": "Espanyol",
        "RCD Espanyol de Barcelona": "Espanyol",
        "Bilbao": "Athletic",
        "Athletic Bilbao": "Athletic",
        "Athletic Club": "Athletic",
        "Celta Vigo": "Celta",
        "RC Celta de Vigo": "Celta",
        "Deportivo Alavés": "Alavés",
        "Deportivo Alaves": "Alavés",
        "Real Betis": "Betis",
        "Real Betis Balompié": "Betis",
        "Oviedo": "Real Oviedo",
        "Girona FC": "Girona",
        "Levante UD": "Levante",
        "Sociedad": "Real Sociedad",

        "Czechia": "Czech Republic",
        "Turkey": "Türkiye",

        "Chelsea FC": "Chelsea",
        "Man City": "Manchester City",
        "Inter Milan": "Inter",
        "Dortmund": "Borussia Dortmund",
        "B. Dortmund": "Borussia Dortmund",
        "Bayern": "Bayern Munich",
        "Bayern München": "Bayern Munich",
        "FC Bayern München": "Bayern Munich",
        "Atl. Madrid": "Atlético",
        "Atletico": "Atlético",
        "Atlético Madrid": "Atlético",
        # "Atlético de Madrid": "Atlético",
        "Paris Saint-Germain": "PSG",
        "Paris SG": "PSG",
        "Psg": "PSG",
        "Seattle Sounders": "Seattle",
        "S. Sounders": "Seattle",
        "Seattle Sounders FC": "Seattle",
        "Salzburg": "RB Salzburg",
        "Red Bull Salzburg": "RB Salzburg",
        "Al-Hilal SFC": "Al-Hilal",
        "Al Hilal": "Al-Hilal",
        "Al Ahly SC": "Ahly SC",
        "Al Ahly FC": "Ahly SC",
        "Al-Ahly": "Ahly SC",
        "Al Ahly": "Ahly SC",
        "Ulsan HD FC": "Ulsan HD",
        "Ulsan Hyundai": "Ulsan HD",
        "Ulsan Hd": "Ulsan HD",
        "Mamelodi Sundowns": "Sundowns",
        "Mamelodi Sundowns FC": "Sundowns",
        "Wydad Casablanca": "Wydad AC",
        "ES Tunis": "Esperance",
        "Espérance Tunis": "Esperance",
        "Esperance de Tunis": "Esperance",
        "Es Tunis": "Esperance",
        "Los Ángeles": "Los Ángeles FC",
        "Los Angeles FC": "Los Ángeles FC",
        "Los Angeles": "Los Ángeles FC",
        "Inter Miami CF": "Inter Miami",
        "Urawa Red Diamonds": "Urawa Reds",
        "FC Porto": "Porto",
        "Botafogo FR": "Botafogo",
        "Al-Ain FC": "Al-Ain",
        "Al Ain": "Al-Ain",
        "Fluminense FC": "Fluminense",
        "CF Pachuca": "Pachuca",
        "Bodoe Glimt": "Bodø/Glimt",
        "FC København": "Copenhagen",
        "FC Kobenhavn": "Copenhagen",
        "Karabakh Agdam": "Qarabag",
        "St Gillis": "Saint-Gilloise",
        "Paphos": "Pafos",
        "Wolves": "Wolverhampton",
        "Wolverhampton Wanderers": "Wolverhampton",
        "Rennes": "Rennais",
        "Gijón": "Sporting",
        "Gijon": "Sporting",
        "Sporting Gijón": "Sporting",
        "Sporting Gijon": "Sporting",
        "Santander": "Racing",
        "Andorra CF": "FC Andorra",
        "Man Utd": "Manchester United",
        "Man United": "Manchester United",
        "Bayer 04 Leverkusen": "Bayer Leverkusen",
        "SK Slavia Praha": "Slavia Prag",
        "Burgos Club de Fútbol": "Burgos CF",
        "Olympiakos": "Olympiacos",
        "Slavia Praha": "Slavia Prag",
    }
    # Return the normalized name if it exists in the dictionary; otherwise, return the original name
    fallback = my_string
    if fallback_none:
        # otherwise, return None
        fallback = None
    return normalization_dict.get(my_string, fallback)


def find_string_positions(string_list, target_string):
    positions = []
    for idx, string in enumerate(string_list):
        if target_string in string:
            positions.append(idx)
    return positions


def is_valid_league_dict(league, min_teams=10):
    if not isinstance(league, dict):
        return False
    if "data" in league: # For Biwenger data
        if not isinstance(league["data"], dict): # or "data" not in league
            return False
        # 2. Check if 'teams' is valid
        if "teams" not in league["data"]:
            return False
        teams = league["data"]["teams"]
        if not isinstance(teams, dict):
            return False
        # 3. Minimum number of teams
        if len(teams) < min_teams:
            return False
        # 4. Check if 'players' is valid
        if "players" not in league["data"]:
            return False
        players = league["data"]["players"]
        if not isinstance(players, dict):
            return False
        # 5. Minimum number of players
        if len(players) < 100:
            return False
        return True

    else:
        if len(league) < min_teams:
            return False
        for team, players in league.items():
            if isinstance(players, dict):
                if len(players) < 11:
                    return False
            if isinstance(players, list):
                if len(players) < 5:
                    return False
    return True


def add_old_data_to_teams(teams_data, teams_old_file_name, file_type="json"):
    if "data" in teams_data: # For Biwenger data
        return teams_data

    teams_old_data = read_dict_data(teams_old_file_name, file_type)
    if not isinstance(teams_data, dict) or not isinstance(teams_old_data, dict):
        return teams_data
    # Add players that were in OLD Data and not here
    for team, players in teams_data.items():
        if team in teams_old_data and isinstance(players, dict) and isinstance(teams_old_data[team], dict):
            for old_player, old_player_val in teams_old_data[team].items():
                if old_player not in teams_data[team]:
                    teams_data[team][old_player] = old_player_val
    return teams_data


def correct_teams_with_old_data(teams_data, teams_old_file_name, num_teams=10, file_type="json"):
    if "data" in teams_data: # For Biwenger data
        return teams_data

    teams_old_data = read_dict_data(teams_old_file_name, file_type)
    if not isinstance(teams_data, dict) or not isinstance(teams_old_data, dict):
        return teams_data
    # Check I have all the teams I used to have
    if len(teams_data) < num_teams <= len(teams_old_data):
        for old_team in teams_old_data:
            if old_team not in teams_data:
                teams_data[old_team] = teams_old_data[old_team]
    # Add players that were in OLD Data and not here
    teams_data = add_old_data_to_teams(teams_data, teams_old_file_name, file_type=file_type)
    # Correct team data with not a lot of data
    for team, players in teams_data.items():
        if isinstance(players, dict):
            if team in teams_old_data and len(players) < 11 <= len(teams_old_data[team]):
                teams_data[team].update(teams_old_data[team])
        if isinstance(players, list):
            if team in teams_old_data and len(players) < 5 <= len(teams_old_data[team]):
                teams_data[team] = teams_old_data[team]
    return teams_data


# def overwrite_dict_data(dict_data, file_name, ignore_valid_file=False, ignore_old_data=False, file_type="json"):
def overwrite_dict_data(dict_data, file_name, ignore_valid_file=True, ignore_old_data=False, file_type="json"):
    file_path = os.path.join(ROOT_DIR, 'json_files', f"{file_name}.json")
    file_path_old = os.path.join(ROOT_DIR, 'json_files', f"{file_name}_OLD.json")
    if file_type and isinstance(file_type, str):
        file_path = os.path.join(ROOT_DIR, f"{file_type}_files", f"{file_name}.{file_type}")
        file_path_old = os.path.join(ROOT_DIR, f"{file_type}_files", f"{file_name}_OLD.{file_type}")
    if not ignore_old_data:
        # Check if the data is not valid, and if so, fill it with old data
        if not is_valid_league_dict(dict_data) or ignore_valid_file:
            if os.path.exists(file_path):
                if os.path.exists(file_path_old):
                    dict_data = correct_teams_with_old_data(dict_data, file_name, file_type=file_type)
        # If data is valid now, we use old data that we missed
        if is_valid_league_dict(dict_data) or ignore_valid_file:
            if os.path.exists(file_path):
                if os.path.exists(file_path_old):
                    dict_data = add_old_data_to_teams(dict_data, file_name, file_type=file_type)
    # If data is valid again, we overwrite
    if is_valid_league_dict(dict_data) or ignore_valid_file:
        # Check if the file exists and delete it
        if os.path.exists(file_path):
            if os.path.exists(file_path_old):
                os.remove(file_path_old)
            shutil.copy(file_path, file_path_old)
            os.remove(file_path)
        write_dict_data(dict_data, file_name, file_type)


def write_dict_to_csv(dict_data, file_name):
    with open(ROOT_DIR + "/csv_files/" + file_name + ".csv", 'w', encoding='utf-8', newline='') as csv_file:  # Specify newline parameter
        writer = csv.writer(csv_file)
        for key, value in dict_data.items():
            writer.writerow([key, value])


def convert_value(value):
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def read_dict_from_csv(file_name):
    with open(ROOT_DIR + "/csv_files/" + file_name + ".csv", encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        mydict = dict(reader)
        mydict = {key: convert_value(value) for key, value in mydict.items()}
        return mydict


def write_dict_to_json(dict_data, file_name):
    file_path = os.path.join(ROOT_DIR, "json_files", f"{file_name}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(dict_data, f, ensure_ascii=False, indent=2)


def read_dict_from_json(file_name):
    file_path = os.path.join(ROOT_DIR, "json_files", f"{file_name}.json")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def read_dict_data(file_name, file_type="json"):
    dict_data = None
    if file_type == "csv" and os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
        dict_data = read_dict_from_csv(file_name)
    elif file_type == "json" and os.path.isfile(ROOT_DIR + '/json_files/' + file_name + '.json'):
        dict_data = read_dict_from_json(file_name)
    else:
        if os.path.isfile(ROOT_DIR + '/json_files/' + file_name + '.json'):
            dict_data = read_dict_from_json(file_name)
    return dict_data


def write_dict_data(dict_data, file_name, file_type="json"):
    if file_type == "csv":
        write_dict_to_csv(dict_data, file_name)
    elif file_type == "json":
        write_dict_to_json(dict_data, file_name)
    else:
        write_dict_to_json(dict_data, file_name)


def delete_file(file_name, file_type="json"):
    file_path = os.path.join(ROOT_DIR, 'json_files', f"{file_name}.json")
    if file_type and isinstance(file_type, str):
        file_path = os.path.join(ROOT_DIR, f"{file_type}_files", f"{file_name}.{file_type}")
    try:
        os.remove(file_path)
        print(f"File '{file_path}' has been deleted successfully.")
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    except PermissionError:
        print(f"Permission denied: Unable to delete '{file_path}'.")
    except Exception as e:
        print(f"An error occurred while deleting the file '{file_path}': {e}")


def create_driver(keep_alive=True):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.page_load_strategy = "eager"
    chrome_options.add_argument("--disable-search-engine-choice-screen")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("enable-automation")
    chrome_options.add_argument("--window-size=1920,1080")  # Set the window size
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--dns-prefetch-disable")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    return webdriver.Chrome(keep_alive=keep_alive, options=chrome_options)


def get_working_proxy(
        target_url: str,
        headers: dict | None = None,
        max_proxies: int | None = None,
        timeout: float = 5.0
) -> str:
    """
    Fetches a fresh list of public proxies, tests them against `target_url`
    using the supplied `headers`, and returns the first proxy that works.

    :param target_url: The URL to test connectivity through the proxy.
    :param headers:    (Optional) A dict of headers to send with each test request.
    :param max_proxies:(Optional) Max number of proxies to try (None = all).
    :param timeout:    Request timeout in seconds.
    :return:           A working proxy string in "IP:port" format.
    :raises RuntimeError: If no proxy succeeds.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 1) Fetch and parse the raw proxy list
    # html = requests.get("https://free-proxy-list.net/", verify=False).text
    html = tls_requests.get("https://free-proxy-list.net/", verify=False).text
    soup = BeautifulSoup(html, "html.parser")
    raw = soup.find("textarea", {"class": "form-control"}).get_text()
    lines = raw.splitlines()[2:]  # skip header lines
    proxy_list = [line.strip() for line in lines if line.strip()]

    # 2) Test each proxy
    for idx, proxy in enumerate(proxy_list):
        if max_proxies and idx >= max_proxies:
            break
        try:
            # resp = requests.get(
            resp = tls_requests.get(
                target_url,
                proxies={"https": proxy},
                headers=headers or {},
                timeout=timeout,
                verify=False
            )
            body = resp.text.lstrip()
            # only accept if status 200 and body starts with an HTML doctype
            if resp.status_code == 200 and body.startswith("<!DOCTYPE html"):
                return proxy
        except Exception:
            continue

    raise RuntimeError("No working proxy found")


# Define a custom exception for timeout
class CustomTimeoutException(Exception):
    pass


# Define a custom exception for non-200 HTTP status codes
class CustomConnectionException(Exception):
    """Custom exception for non-200 HTTP status codes."""
    pass


# A wrapper to run each iteration with a timeout
def run_with_timeout(timeout, task):
    with stopit.ThreadingTimeout(timeout) as to_ctx:
        result = task()  # Run the task
    if to_ctx.state == to_ctx.TIMED_OUT:
        print("Timeout occurred during task execution.")
        raise CustomTimeoutException("The task took too long and was stopped.")
    return result
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     future = executor.submit(task)
    #     try:
    #         result = future.result(timeout=timeout)  # Wait for the result with a timeout
    #         return result  # Return the result if task completes in time
    #     except concurrent.futures.TimeoutError:
    #         print("Timeout occurred during task execution.")
    #         raise CustomTimeoutException("The task took too long and was stopped.")



def percentile_ranks_dict(array):
    """
    Returns a dict {value: percentile_rank} where percentile_rank is in [0, 1].
    All duplicate values share the same rank.
    """
    arr = np.array(array)
    return {x: np.sum(arr <= x) / len(arr) for x in np.unique(arr)}


# Instead of computing percentiles manually, we can normalize directly to 0-1
def percentile_rank(array, score):
    if not array:  # empty list
        return 0.0
    return np.sum(np.array(array) <= score) / len(array)


# find_similar_string("Trent", ["Trent Alexander-Arnold", ], verbose=True)
