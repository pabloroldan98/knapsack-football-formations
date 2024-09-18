import ast
import os
import shutil

from unidecode import unidecode
import difflib
from fuzzywuzzy import fuzz
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


def cleaned_string(s):
    res = s
    return unidecode(str(res)).lower().replace(" ", "").replace("-", "")

def format_string(s):
    words = s.split()
    if len(words) > 1:
        return words[0][0] + '. ' + ' '.join(words[1:])
    return s


def find_similar_string(my_string, string_list, similarity_threshold=0.8, verbose=False, is_formatted=False):
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
        print(f"Most similar string for \"{my_string}\": {most_similar_string} ({max_similarity*100:.2f} %)")
    if max_similarity >= similarity_threshold:
        return most_similar_string
    return None


def find_string_positions(string_list, target_string):
    positions = []
    for idx, string in enumerate(string_list):
        if target_string in string:
            positions.append(idx)
    return positions


def is_valid_teams_dict(teams, num_teams=10):
    if not isinstance(teams, dict):
        return False
    if len(teams) < num_teams:
        return False
    for team, players in teams.items():
        if isinstance(players, dict):
            if len(players) < 11:
                return False
        if isinstance(players, list):
            if len(players) < 5:
                return False
    return True


def correct_teams_with_old_data(teams_data, teams_old_file_name, num_teams=10):
    teams_old_data = read_dict_from_csv(teams_old_file_name)
    if not isinstance(teams_data, dict) or not isinstance(teams_old_data, dict):
        return teams_data
    if len(teams_data) < num_teams <= len(teams_old_data):
        for old_team in teams_old_data:
            if old_team not in teams_data:
                teams_data[old_team] = teams_old_data[old_team]
    for team, players in teams_data.items():
        if isinstance(players, dict):
            if team in teams_old_data and len(players) < 11 <= len(teams_old_data[team]):
                teams_data[team].update(teams_old_data[team])
        if isinstance(players, list):
            if team in teams_old_data and len(players) < 5 <= len(teams_old_data[team]):
                teams_data[team].update(teams_old_data[team])
    return teams_data


def overwrite_dict_to_csv(dict_data, file_name, ignore_valid_file=False):
    file_path = ROOT_DIR + '/csv_files/' + file_name + '.csv'
    file_path_old = ROOT_DIR + '/csv_files/' + file_name + '_OLD.csv'
    # Check if the data is not valid, and if so, fill it with old data
    if not is_valid_teams_dict(dict_data) or ignore_valid_file:
        if os.path.exists(file_path):
            if os.path.exists(file_path_old):
                dict_data = correct_teams_with_old_data(dict_data, file_name + "_OLD")
    # If data is valid now, we overwrite
    if is_valid_teams_dict(dict_data) or ignore_valid_file:
        # Check if the file exists and delete it
        if os.path.exists(file_path):
            if os.path.exists(file_path_old):
                os.remove(file_path_old)
            shutil.copy(file_path, file_path_old)
            os.remove(file_path)
        write_dict_to_csv(dict_data, file_name)


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


def delete_file(file_name):
    file_path = ROOT_DIR + '/csv_files/' + file_name + '.csv'
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
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    return webdriver.Chrome(keep_alive=keep_alive, options=chrome_options)
