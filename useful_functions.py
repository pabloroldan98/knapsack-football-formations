import ast
import hashlib
import json
import os
import secrets
import shutil
import tempfile
import threading

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
from filelock import FileLock

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
LOCK_DIR = os.path.join(ROOT_DIR, ".locks")
FILE_LOCK_TIMEOUT = 300


# random header pool
HEADER_POOL = [
    # Chrome / Windows 10
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.7727.50 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.7642.112 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.7598.177 Safari/537.36"
        )
    },

    # Chrome / Windows 11
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.7727.49 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.7642.95 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/144.0.7541.98 Safari/537.36"
        )
    },

    # Chrome / macOS Monterey
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7_6) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.7727.50 Safari/537.36"
        )
    },

    # Chrome / macOS Ventura
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.7727.49 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_9) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.7642.112 Safari/537.36"
        )
    },

    # Chrome / macOS Sonoma
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.7727.50 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.7642.95 Safari/537.36"
        )
    },

    # Chrome / Linux
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.7727.49 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.7642.112 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.7598.177 Safari/537.36"
        )
    },

    # Chrome / Ubuntu
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.7727.50 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.7642.95 Safari/537.36"
        )
    },

    # Edge / Windows 10
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.3856.97"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.3856.59"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36 Edg/145.0.3800.97"
        )
    },

    # Edge / Windows 11
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.3856.97"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36 Edg/145.0.3800.97"
        )
    },

    # Edge / macOS
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.3856.97"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36 Edg/145.0.3800.97"
        )
    },

    # Firefox / Windows
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) "
            "Gecko/20100101 Firefox/149.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) "
            "Gecko/20100101 Firefox/148.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) "
            "Gecko/20100101 Firefox/147.0"
        )
    },

    # Firefox / macOS
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:149.0) "
            "Gecko/20100101 Firefox/149.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.7; rv:148.0) "
            "Gecko/20100101 Firefox/148.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12.7; rv:147.0) "
            "Gecko/20100101 Firefox/147.0"
        )
    },

    # Firefox / Linux
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) "
            "Gecko/20100101 Firefox/149.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:148.0) "
            "Gecko/20100101 Firefox/148.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) "
            "Gecko/20100101 Firefox/147.0"
        )
    },

    # Safari / macOS Ventura
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7_5) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/26.0 Safari/605.1.15"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_9) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.6 Safari/605.1.15"
        )
    },

    # Safari / macOS Sonoma
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/26.0 Safari/605.1.15"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/26.0 Safari/605.1.15"
        )
    },

    # Safari / macOS Sequoia
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_3) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/26.0 Safari/605.1.15"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_2) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/26.0 Safari/605.1.15"
        )
    },

    # Opera / Windows
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 OPR/131.0.0.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36 OPR/130.0.0.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/144.0.0.0 Safari/537.36 OPR/129.0.0.0"
        )
    },

    # Opera / macOS
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 OPR/131.0.0.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36 OPR/130.0.0.0"
        )
    },

    # Opera / Linux
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 OPR/131.0.0.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36 OPR/130.0.0.0"
        )
    },

    # Slightly older but still believable Chrome variants
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; WOW64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/143.0.7499.40 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux i686) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/142.0.7444.162 Safari/537.36"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7_4) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/143.0.7499.71 Safari/537.36"
        )
    },

    # Slightly older Firefox variants
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:146.0) "
            "Gecko/20100101 Firefox/146.0"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux i686; rv:145.0) "
            "Gecko/20100101 Firefox/145.0"
        )
    },

    # Mixed additional Edge variants
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/144.0.0.0 Safari/537.36 Edg/144.0.3698.98"
        )
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7_6) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/144.0.0.0 Safari/537.36 Edg/144.0.3698.98"
        )
    },
]


def cleaned_string(s):
    res = s
    return unidecode(str(res)).lower().replace(" ", "").replace("-", "")

def format_string(s):
    words = s.split()
    if len(words) > 1:
        return words[0][0] + '. ' + ' '.join(words[1:])
    return s


def find_similar_string(my_string, string_list, similarity_threshold=0.8, verbose=False, is_formatted=False, fallback_none=False):
    if my_string in [
        "Kevin Medina", "Kevin Villodres", "Thuram-Ulien", "Khéphren Thuram", "K. Thuram",
        "Manu Koné", "Kouadio Koné", "Moustapha Mbow", "Mamadou Mbow",
        "Ben Doak", "Ben Gannon-Doak",
    ]:
        similarity_threshold = 0.45
    if my_string in [
        "Álvaro Carreras", "Álvaro Fernández", "Á. Fernandez", "Pape Matar Sarr", "Pape Sarr", "Frank Anguissa", "Zambo Anguissa",
        "Luis Javier Suárez", "Luis Javier Suarez", "Luis Suárez", "Luis Suarez",
        "Nueva Zelanda", "New Zealand", "Cabo Verde", "Cape Verde",
    ]:
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
        "Rahim": "Alhassane",
        "A. Rahim": "Alhassane",
        # "Haissem Hassan": "Hassan",
        "H. Hassan": "Haissem Hassan",
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

        "Khéphren Thuram-Ulien": "K. Thuram-Ulien",
        "Khephren Thuram": "K. Thuram-Ulien",
        # "K. Thuram": "K. Thuram-Ulien",
        # "Khéphren Thuram": "K. Thuram-Ulien",
        # "Thuram-Ulien": "K. Thuram-Ulien",
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
        # "José Manuel López": "José López",
        "Erling Braut Haland": "Haaland",
        "Kim Min-Jae": "Min-jae Kim",
        "Kim Min-jae": "Min-jae Kim",
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
        # "Moustapha Mbow": "Mamadou Mbow",
        "Karim Dermane": "Dermane Karim",
        "Hamed Junior Traorè": "Hamed Traoré",
        "Lionel M'Pasi": "Mpasi",
        "Kevin David Medina Renteria": "Kevin Medina Villodres",
        # "Kevin Medina": "Kevin Medina Villodres",
        # "Kevin Villodres": "Kevin Medina Villodres",
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
        "Neofytos Michael": "Michael",
        "Neofytos Michail": "Michael",
        "Oscar Gadeberg Buur": "Oscar Buur",
        # "Luis Javier Suárez": "Luis Suárez",
        # "Luis Javier Suarez": "Luis Suárez",
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
        "S. Berg": "Sepp van den Berg",
        "Elvin Cafarquliyev": "Jafarguliyev",
        "Amad Traoré": "Amad Diallo",
        "Rodri Hernández": "Rodrigo",
        "Olzhas Baibek": "Baybek",
        # "Oso": False,
        "Álvaro": "Álvaro Rodríguez",
        "German V.": "Germán Valera",
        "Junior": "Firpo",
        "Vlachodimos": "Odysseas",
        "Bardghji": "Roony",
        "Kiko F.": "Kiko Femenía",
        # "Mendy": "Batista",
        "Ilyas": "Chaira",
        "A. Ferllo": "Álvaro Fernández",
        "Lucas": "Ahijado",
        "Ismael": "Bekhoucha",
        "Víctor G.": "Víctor García",
        "Javi H.": "Javi Hernández",
        "Adam B.": "Boayar",
        "Youssef": "Yusi Enríquez",
        "Tai Abed Kassus": "Tay Abed",
        "Tai Abed": "Tay Abed",
        "Syver Skundberg Skeide": "Syver Skeide",
        "David Daiber": "David Santos Daiber",
        "Nicols Riestra Coalla": "Nico Riestra",
        "Homam Ahmed": "Homam Al-Amin",
        "Daniel Nicolas Frey": "Daniel Frey",

        "Ahmed Nadhir Benbouali": "N. Benbouali",
        "José López": "Jose Manuel Lopez",
        "Kevin Lenini": "Kevin Pina",
        "Pico": "Roberto Lopes",
        "Rafael Borré": "Santos Borré",
        "Sherel Constancio Floranus": "Sherel Floranus",
        "Trevor Iriving Doornbusch": "T. Doornbusch",
        "Léo Realpe": "Leonardo Realpe",
        "Mahdi Soliman": "E. Soliman",
        "Christopher Baah": "C. Bonsu Baah",
        "Abdul Fatawu Issahaku": "Issahaku Fatawu",
        "Prince Kwabena Adu": "Prince Adu",
        "Louicius Don Deedson": "L. Deedson",
        "Frans Putros": "F. Dhia Putros",
        "Osako Keisuke": "Keisuke Osako",
        "Abdel Rahman Muhammad": "A. Al-Talalga",
        "Mohammad Ali Hasheesh": "M. Abu Hasheesh",
        "Mohammad Al Daoud": "M. Al-Dawoud",
        "Nizar Mahmoud Al-Rashdan": "N. Al-Rashdan",
        "Noor Al-Deen Al Rawabdeh": "N. Al-Rawabdeh",
        "Mohammad Abu Zrayq": "Shararh",
        "Raúl Rangel": "José Rangel",
        "Mehdi Al Harrar": "E. Al Harrar",
        "Mohamed Rabie Hrimat": "M. Hrimat",
        "Felix Horn Myhre": "F. Myhre",
        "Henrik Sælebakke Falchener": "H. Falchener",
        "Benjamin Old": "Ben Old",
        "Gustavo Velázquez": "Víctor Velázquez",
        "Anas Abdulsalam Abweny": "Anas Abweny",
        "Khalid Ali Sabah": "K. Sabah",
        "Mohamed Naceur Almanai": "M. Al-Mannai",
        "Yousef Farahat": "Youssef Ayman",
        "Tholo Thabang Matuludi": "T. Matuludi",
        "Taha Abdi Ali": "Taha Ali",
        "Amine Ben Hmida": "Ben Hamida",
        "Maximilian Arfsten": "Max Arfsten",
        "Tim Weah": "Timothy Weah",
        "Puma Rodríguez": "Jose Luis Rodriguez",
        "Avazbek Ulmasaliyev": "A. Ulmasaliev",
        "Jamshid Iskandarov": "J. Iskanderov",
        "Muhammadrasul Abdumajidov": "M. Abdumazhidov",
        "Nodirbek Abdurazzokov": "N. Abdurazzakov",
        "Figaldo": "Álvaro Fidalgo",
        "Gabriel M.": "Magalhães",
        # "Gabriel Magalhães": "Magalhães",
        "Deedson L.": "L. Deedson",
        "Achraf": "Hakimi",
        "Pico Lopes": "Roberto Lopes",
        "Sosa (Izq.)": "Borna Sosa",
        "Fattouh": "Ahmed Fatouh",
        "Naseeb": "Abdallah Nasib",
        "Abu Hashish": "M. Abu Hasheesh",
        "Al-Taamari": "Mousa Al-Tamari",
        "Gana Gueye": "Idrissa Gueye",
        "Alijonov": "K. Alizhonov",
        "El Mehdi Al Harrar": "E. Al Harrar",
        "Rayyan Ahmed Al-Ali": "R. Al-Ali",
        "Marwan Ateya": "Attia",
        # "Dean Henderson": "Henderson",
        "Hwang Hee-chan": "Hee-chan Hwang",
        "Hwang Hee-Chan": "Hee-chan Hwang",
        "Son Heung-min": "Heung-Min Son",
        "Son Heung-Min": "Heung-Min Son",
        "Yang Hyun-Jun": "Hyun-jun Yang",
        "Yang Hyun-jun": "Hyun-jun Yang",
        "Hwang In-beom": "In-beom Hwang",
        "Hwang In-Beom": "In-beom Hwang",
        "Kim Seung-gyu": "Seung Gyu Kim",
        "Kim Seung-Gyu": "Seung Gyu Kim",
        "Lee Tae-seok": "Tae-seok Lee",
        "Lee Tae-Seok": "Tae-seok Lee",
        "Cho Yu-min": "Yu-min Cho",
        "Cho Yu-Min": "Yu-min Cho",
        "Kim Tae-hyeon": "Tae-hyeon Kim",
        "Kim Tae-Hyeon": "Tae-hyeon Kim",
        "Lee Han-beom": "Han-beom Lee",
        "Lee Han-Beom": "Han-beom Lee",
        "Lee Jae-sung": "Jae Sung Lee",
        "Lee Jae-Sung": "Jae Sung Lee",
        "Seol Young-woo": "Young-woo Seol",
        "Seol Young-Woo": "Young-woo Seol",
        "Paik Seung-ho": "Seung-Ho Paik",
        "Paik Seung-Ho": "Seung-Ho Paik",
        "Lee Kang-in": "Kang-in Lee",
        "Lee Kang-In": "Kang-in Lee",
        "Bae Jun-Ho": "Jun-ho Bae",
        "Bae Jun-ho": "Jun-ho Bae",
        "Kim Jin-Gyu": "Jin-gyu Kim",
        "Kim Jin-gyu": "Jin-gyu Kim",
        "Kim Moon-Hwan": "Moon-hwan Kim",
        "Kim Moon-hwan": "Moon-hwan Kim",
        "Park Jin-seob": "Jin-seob Park",
        "Park Jin-Seob": "Jin-seob Park",
        "Lee Dong-gyeong": "Dong-gyeong Lee",
        "Lee Dong-Gyeong": "Dong-gyeong Lee",
        "Song Bum-Keun": "Bum-keun Song",
        "Song Bum-keun": "Bum-keun Song",
        "Cho Gue-Sung": "Gue-sung Cho",
        "Cho Gue-sung": "Gue-sung Cho",
        "Eom Ji-sung": "Ji-sung Eom",
        "Eom Ji-Sung": "Ji-sung Eom",
        "Lee Gi-Hyuk": "Gi-hyuk Lee",
        "Lee Gi-hyuk": "Gi-hyuk Lee",
        "Cho Wi-je": "Wi-je Cho",
        "Cho Wi-Je": "Wi-je Cho",
        "Waldemar Anton": "Anton",
        "Wilfried Stephane Singo": "Wilfried Singo",
        "Juan José Cáceres": "J. Cáceres",
        "Juan Jose Caceres": "J. Cáceres",
        # "Ben Doak": "Ben Gannon-Doak", # en mundial y premier
        "Yaya Sithole": "Sphephelo Sithole",
        "Kerem Aktrkoglu": "Aktürkoğlu",
        "Mert Mldr": "Müldür",
        "Dailon Livramento": "Dailon Rocha",
        "Yasser Ahmed Ibrahim El Hanafi": "Yasser Ibrahim",
        "Yazeed Mo'ien Hasan Abulaila": "Yazeed Abulaila",
        "Husam Ali Mohammad Abu Dahab": "Husam Abu Dahab",
        "Abdallah Mousa Musallam Nasib": "Abdallah Nasib",
        "Nizar Mahmoud Ahmed Al Rashdan": "N. Al-Rashdan",
        "Jorge Eduardo Sanchez": "Jorge Sánchez",
        "Maxime Teremoana Crocombe": "Max Crocombe",
        "Gatito Fernández": "Roberto Fernández",
        "Lucas Michel Mendes": "Lucas Mendes",
        "Mohammad Naceur Al Mannai": "M. Al-Mannai",
        "Alexander Isak": "Isak",
        "Odildzhon Hamrobekov": "O. Khamrobekov",
        "Sherzod Nasrullayev": "S. Nasrullaev",
        "El Mahdi Soliman": "E. Soliman",
        "Antonio Rüdiger": "Rüdiger",
        "Yassine Bounou": "Bono",
        "Jassem Gaber": "Jassem Abdulsallam",
        "Bamba Dieng": "Ahmadou Dieng",
        "Javi Montero": "Francisco Montero",
        "Noureddin Bani Ateyah": "N. Bani Attiah",
        "Rahman Baba": "Baba Rahman",
        "Cameron Devlin": "Cammy Devlin",
        # "Emiliano Martínez": "Dibu Martínez", # en mundial, premier y mundialito
        "José Manuel López": "Flaco López",
        "Antonin Svoboda": "Michael Svoboda",
        "Joris Kayembe": "Kayembe",
        "Junnosuke Suzuki": "Suzuki",
        "Marcus Holmgren Pedersen": "Marcus Pedersen",
        "Édgar Bárcenas": "Yoel Bárcenas",
        "Yehvann Diouf": "Diouf",
        "E. Kayembe": "Edo Kayembe",
        "E. Safi": "Ehsan Haji Safi",
        "A. Fadhil": "A. Basil Fadhil",
        "M. Mahmoud": "M. Belhadj Mahmoud",
        "Odeh Burhan Shehade Fakhoury": "Odeh Fakhoury",
        "Mahmud Ibrahim Abunada": "Mahmoud Abunada",
        "Odiljon Hamrobekov": "O. Khamrobekov",
        "Khojiakbar Alijonov": "K. Alizhonov",
        # "AAAAAAAA": "BBBBBBB",
        # "AAAAAAAA": "BBBBBBB",
        # "AAAAAAAA": "BBBBBBB",

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

        "Irlanda": "Ireland",
        "Gales": "Wales",
        "Argentina": "Argentina",
        "Australia": "Australia",
        "Austria": "Austria",
        "Colombia": "Colombia",
        "Ecuador": "Ecuador",
        "Paraguay": "Paraguay",
        "Portugal": "Portugal",
        "Senegal": "Senegal",
        "Uruguay": "Uruguay",
        "Czechia": "Czech Republic",
        "República Checa": "Czech Republic",
        "Rep. Checa": "Czech Republic",
        "Turkey": "Türkiye",
        "Turquía": "Türkiye",
        "Corea del Sur": "South Korea",
        "Corea Del Sur": "South Korea",
        "España": "Spain",
        "México": "Mexico",
        "Sudáfrica": "South Africa",
        "Alemania": "Germany",
        "Arabia Saudí": "Saudi Arabia",
        "Argelia": "Algeria",
        "Bosnia y Herzegovina": "Bosnia",
        "Bosnia": "Bosnia",
        "Brasil": "Brazil",
        "Bélgica": "Belgium",
        "Canadá": "Canada",
        "Catar": "Qatar",
        "Congo (RDC)": "Congo (DRC)",
        "Congo (Rdc)": "Congo (DRC)",
        "RD Congo": "Congo (DRC)",
        "DR Congo": "Congo (DRC)",
        "Democratic Republic of the Congo": "Congo (DRC)",
        "Costa de Marfil": "Ivory Coast",
        "Côte d'Ivoire": "Ivory Coast",
        "Cote D'ivoire": "Ivory Coast",
        "Costa De Marfil": "Ivory Coast",
        "Croacia": "Croatia",
        "Curazao": "Curaçao",
        "Egipto": "Egypt",
        "Escocia": "Scotland",
        "Estados Unidos": "US",
        "Estados Unidos de América": "US",
        "EEUU": "US",
        "United States": "US",
        "United States of America": "US",
        "USA": "US",
        "Francia": "France",
        "Gana": "Ghana",
        "Haití": "Haiti",
        "Inglaterra": "England",
        "Irak": "Iraq",
        "Irán": "Iran",
        "Japón": "Japan",
        "Jordania": "Jordan",
        "Marruecos": "Morocco",
        "Noruega": "Norway",
        "Panamá": "Panama",
        "Países Bajos": "Netherlands",
        "Holanda": "Netherlands",
        "Suecia": "Sweden",
        "Suiza": "Switzerland",
        "Túnez": "Tunisia",
        "Uzbekistán": "Uzbekistan",
        # "Nueva Zelanda": "New Zealand",  # no hasta que pongan el nombre en inglés en https://cf.biwenger.com/api/v2/competitions/world-cup/data?lang=en&score=1
        # "Cabo Verde": "Cape Verde",  # same
        # "AAAAAAAA": "BBBBBBB",
        # "AAAAAAAA": "BBBBBBB",
        # "AAAAAAAA": "BBBBBBB",

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
        "Paris": "PSG",
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
        "Karabakh Agdam": "Qarabag FK",
        "Qarabag": "Qarabag FK",
        "St Gillis": "Saint-Gilloise",
        "Union SG": "Saint-Gilloise",
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
        "Sporting CP": "Sporting Portugal",

        "Kouadio Koné": "Manu Koné",  # seriea y mundial
        "Dibu Martínez": "Emiliano Martínez",  # en mundial, premier y mundialito
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


def _lock_path_for_file(file_path):
    os.makedirs(LOCK_DIR, exist_ok=True)
    digest = hashlib.sha1(os.path.abspath(file_path).encode("utf-8")).hexdigest()
    return os.path.join(LOCK_DIR, f"{digest}.lock")


def _dict_data_file_lock(file_path):
    return FileLock(_lock_path_for_file(file_path), timeout=FILE_LOCK_TIMEOUT)


def _atomic_write_file(file_path, write_fn, mode="w", encoding="utf-8", newline=None):
    dir_name = os.path.dirname(file_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=dir_name)
    os.close(fd)
    open_kwargs = {"mode": mode, "encoding": encoding}
    if newline is not None:
        open_kwargs["newline"] = newline
    with open(tmp_path, **open_kwargs) as f:
        write_fn(f)
    os.replace(tmp_path, file_path)


def _atomic_copy_file(src_path, dst_path):
    dir_name = os.path.dirname(dst_path) or "."
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=dir_name)
    os.close(fd)
    shutil.copy2(src_path, tmp_path)
    os.replace(tmp_path, dst_path)


# def overwrite_dict_data(dict_data, file_name, ignore_valid_file=False, ignore_old_data=False, file_type="json"):
def overwrite_dict_data(dict_data, file_name, ignore_valid_file=True, ignore_old_data=False, file_type="json", compact_list_items=False):
    file_path = os.path.join(ROOT_DIR, 'json_files', f"{file_name}.json")
    file_path_old = os.path.join(ROOT_DIR, 'json_files', f"{file_name}_OLD.json")
    correct_data_file = file_name
    correct_data_file_path = os.path.join(ROOT_DIR, 'json_files', f"{correct_data_file}_OLD.json")
    if file_type and isinstance(file_type, str):
        file_path = os.path.join(ROOT_DIR, f"{file_type}_files", f"{file_name}.{file_type}")
        file_path_old = os.path.join(ROOT_DIR, f"{file_type}_files", f"{file_name}_OLD.{file_type}")
    with _dict_data_file_lock(file_path):
        if not ignore_old_data:
            # Check if the data is not valid, and if so, fill it with old data
            if not is_valid_league_dict(dict_data) or ignore_valid_file:
                if os.path.exists(correct_data_file_path):
                    dict_data = correct_teams_with_old_data(dict_data, correct_data_file, file_type=file_type)
            # If data is valid now, we use old data that we missed
            if is_valid_league_dict(dict_data) or ignore_valid_file:
                if os.path.exists(correct_data_file_path):
                    dict_data = add_old_data_to_teams(dict_data, correct_data_file, file_type=file_type)
        # If data is valid again, we overwrite
        if is_valid_league_dict(dict_data) or ignore_valid_file:
            if os.path.exists(file_path):
                _atomic_copy_file(file_path, file_path_old)
            write_dict_data(dict_data, file_name, file_type, _skip_lock=True, compact_list_items=compact_list_items)


def write_dict_to_csv(dict_data, file_name, _skip_lock=False):
    file_path = os.path.join(ROOT_DIR, "csv_files", f"{file_name}.csv")

    def _write():
        def write_fn(csv_file):
            writer = csv.writer(csv_file)
            for key, value in dict_data.items():
                writer.writerow([key, value])

        _atomic_write_file(file_path, write_fn, newline="")

    if _skip_lock:
        _write()
    else:
        with _dict_data_file_lock(file_path):
            _write()


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


def _format_dict_json_compact_list_items(dict_data):
    lines = ["{"]
    items = list(dict_data.items())
    for idx, (key, value) in enumerate(items):
        if isinstance(value, list) and value and all(isinstance(item, list) for item in value):
            entries = ",\n    ".join(json.dumps(item, ensure_ascii=False) for item in value)
            block = f'  {json.dumps(key, ensure_ascii=False)}: [\n    {entries}\n  ]'
        else:
            block = json.dumps({key: value}, ensure_ascii=False, indent=2)[1:-1].strip()
        lines.append(block + ("," if idx < len(items) - 1 else ""))
    lines.append("}")
    return "\n".join(lines)


def write_dict_to_json(dict_data, file_name, _skip_lock=False, compact_list_items=False):
    file_path = os.path.join(ROOT_DIR, "json_files", f"{file_name}.json")

    def _write():
        def write_fn(f):
            if compact_list_items:
                f.write(_format_dict_json_compact_list_items(dict_data))
            else:
                json.dump(dict_data, f, ensure_ascii=False, indent=2)

        _atomic_write_file(file_path, write_fn)

    if _skip_lock:
        _write()
    else:
        with _dict_data_file_lock(file_path):
            _write()


def read_dict_from_json(file_name):
    file_path = os.path.join(ROOT_DIR, "json_files", f"{file_name}.json")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def dict_data_file_path(file_name, file_type="json"):
    if file_type == "csv":
        return os.path.join(ROOT_DIR, "csv_files", f"{file_name}.csv")
    return os.path.join(ROOT_DIR, "json_files", f"{file_name}.json")


def dict_data_file_exists(file_name, file_type="json"):
    return os.path.isfile(dict_data_file_path(file_name, file_type))


def read_dict_data_local_only(file_name, file_type="json"):
    if not dict_data_file_exists(file_name, file_type):
        return None
    data = read_dict_data(file_name, file_type)
    return {} if data is None else data


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


def write_dict_data(dict_data, file_name, file_type="json", _skip_lock=False, compact_list_items=False):
    if file_type == "csv":
        write_dict_to_csv(dict_data, file_name, _skip_lock=_skip_lock)
    elif file_type == "json":
        write_dict_to_json(dict_data, file_name, _skip_lock=_skip_lock, compact_list_items=compact_list_items)
    else:
        write_dict_to_json(dict_data, file_name, _skip_lock=_skip_lock, compact_list_items=compact_list_items)


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


def _normalize_proxy(p: str) -> str:
    p = (p or "").strip()
    if not p:
        return p
    return p if "://" in p else f"http://{p}"  # tls_requests needs scheme


def _is_sofascore_challenge(text: str) -> bool:
    try:
        data = json.loads(text)
        return isinstance(data, dict) and data.get("error", {}).get("reason") == "challenge"
    except Exception:
        return False


def get_working_proxy(
    target_url: str,
    headers: dict | None = None,
    max_proxies: int | None = 100,
    timeout: float = 6.0,
) -> str:
    """
    Returns a working proxy string like "http://IP:port".
    Tests proxies from free-proxy-list.net against target_url using tls_requests.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    html = tls_requests.get("https://free-proxy-list.net/", verify=False).text
    soup = BeautifulSoup(html, "html.parser")
    raw = soup.find("textarea", {"class": "form-control"}).get_text()
    lines = raw.splitlines()[2:]  # skip header lines
    proxy_list = [line.strip() for line in lines if line.strip()]

    tried = 0
    for proxy in proxy_list:
        if max_proxies and tried >= max_proxies:
            break
        tried += 1

        proxy = _normalize_proxy(proxy)

        try:
            resp = tls_requests.get(
                target_url,
                proxy=proxy,               # <-- IMPORTANT: use `proxy=...` not proxies dict
                headers=headers or {},
                verify=False,
                timeout=timeout,
            )

            text = (resp.text or "").lstrip()

            # Accept any HTTP 200 that isn't the SofaScore "challenge" JSON
            if resp.status_code == 200 and not _is_sofascore_challenge(text) and text.startswith("<!DOCTYPE html"):
                return proxy

        except Exception:
            continue

    raise RuntimeError(f"No working proxy found (tried {tried})")


# Some sites (e.g. SofaScore) block GitHub Actions / datacenter IPs at the
# network level (HTTP 403), even with valid browser-like headers. When that
# happens we route the request through the Tor SOCKS proxy, which gives us a
# residential-looking exit IP. Tor must be installed and running for this to
# connect (the CI workflows take care of that).
TOR_PROXY = os.getenv("TOR_PROXY", "socks5://127.0.0.1:9050")
# SofaScore (Cloudflare) blocks many Tor exit-node IPs, so a given circuit may
# return 403 for every endpoint/fingerprint while another exits cleanly. We
# therefore retry through fresh Tor circuits until one isn't blocked. Tor builds
# a separate circuit per distinct SOCKS username/password (IsolateSOCKSAuth is
# on by default), so we just vary the SOCKS credentials to get a new exit IP.
TOR_CIRCUIT_RETRIES = int(os.getenv("TOR_CIRCUIT_RETRIES", "12"))
# Even through Tor, SofaScore rejects some TLS fingerprints (e.g. chrome_133
# returns 403 for every endpoint), so we rotate over known-good identifiers and
# keep the one that works. Add/remove entries here if SofaScore starts/stops
# accepting a given fingerprint.
TOR_CLIENT_IDENTIFIERS = [
    "safari_16_0",
    "safari_ios_17_0",
    "safari_ios_18_0",
    "okhttp4_android_13",
    "okhttp4_android_12",
    "firefox_132",
    "firefox_120",
    "chrome_131",
    "chrome_124",
    "chrome_120",
    # chrome_133 returns 403 for every endpoint even through Tor
]


def _isolated_tor_proxy():
    """
    Return the Tor SOCKS proxy URL with random credentials. Tor isolates streams
    by SOCKS auth, so unique credentials force a brand-new circuit (and usually a
    different exit IP), letting us route around blocked exit nodes.
    """
    scheme, _, host = TOR_PROXY.partition("://")
    return f"{scheme}://{secrets.token_hex(8)}:tor@{host}"


def _endpoint_key(url):
    """
    Group URLs by endpoint "shape", ignoring the variable parts (numeric ids and
    the slug that precedes them). E.g. every team page collapses to
    "/team/football/{slug}/{id}" and every player summary to
    "/api/v1/{slug}/{id}/last-year-summary", so a 403 on one team/player marks
    the whole endpoint as blocked.
    """
    from urllib.parse import urlparse

    segments = urlparse(url).path.strip("/").split("/")
    out = []
    for i, seg in enumerate(segments):
        if seg.isdigit():
            out.append("{id}")
        elif i + 1 < len(segments) and segments[i + 1].isdigit():
            out.append("{slug}")
        else:
            out.append(seg)
    return "/" + "/".join(out)


class _TorRequests:
    """
    Tor-backed counterpart to tls_requests. `tor_requests.get(...)` makes the
    request through the Tor SOCKS proxy and remembers the endpoint as blocked,
    so callers can use `tor_requests.is_endpoint_blocked(url)` to skip the
    (doomed) direct attempt for the rest of the run:

        if tor_requests.is_endpoint_blocked(url):
            resp = tor_requests.get(url, headers=headers, verify=False)
        else:
            resp = tls_requests.get(url, headers=headers, verify=False)
            if resp.status_code == 403:
                resp = tor_requests.get(url, headers=headers, verify=False)

    Each call retries through fresh Tor circuits (new exit IPs) until one is not
    blocked, rotating TOR_CLIENT_IDENTIFIERS along the way and remembering the
    fingerprint that worked for later calls.
    """

    def __init__(self):
        self._blocked = set()
        self._lock = threading.Lock()
        self._preferred_identifier = None
        self._preferred_proxy = None

    def is_endpoint_blocked(self, url):
        with self._lock:
            return _endpoint_key(url) in self._blocked

    def get(self, url, **kwargs):
        with self._lock:
            self._blocked.add(_endpoint_key(url))

        kwargs.pop("proxy", None)
        kwargs.pop("client_identifier", None)

        # Try the identifier/circuit that worked last first, then rotate.
        with self._lock:
            preferred_identifier = self._preferred_identifier
            preferred_proxy = self._preferred_proxy
        identifiers = list(TOR_CLIENT_IDENTIFIERS)
        if preferred_identifier in identifiers:
            identifiers.remove(preferred_identifier)
            identifiers.insert(0, preferred_identifier)

        # Each attempt uses a fresh circuit (new exit IP) and a rotating
        # identifier, so we route around both blocked exit nodes and rejected
        # fingerprints. The first attempt reuses the last working circuit so we
        # don't rebuild one on every call once we found a clean exit node.
        last_response = None
        for attempt in range(TOR_CIRCUIT_RETRIES):
            identifier = identifiers[attempt % len(identifiers)]
            proxy = preferred_proxy if attempt == 0 and preferred_proxy else _isolated_tor_proxy()
            try:
                response = tls_requests.get(
                    url,
                    client_identifier=identifier,
                    proxy=proxy,
                    **kwargs,
                )
            except Exception:
                continue
            last_response = response
            if response.status_code != 403:
                with self._lock:
                    self._preferred_identifier = identifier
                    self._preferred_proxy = proxy
                return response
        return last_response


tor_requests = _TorRequests()


# Define a custom exception for timeout
class CustomTimeoutException(Exception):
    pass


# Define a custom exception for non-200 HTTP status codes
class CustomConnectionException(Exception):
    """Custom exception for non-200 HTTP status codes."""
    pass


# Define a custom exception for not found elements
class CustomMissingException(Exception):
    """Custom exception for missing elements."""
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
