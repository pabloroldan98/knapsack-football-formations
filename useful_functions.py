import ast
import os
import shutil

from unidecode import unidecode
import difflib
from fuzzywuzzy import fuzz
import csv

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


def overwrite_dict_to_csv(dict_data, file_name):
    if is_valid_teams_dict(dict_data):
        file_path = ROOT_DIR + '/csv_files/' + file_name + '.csv'
        # Check if the file exists and delete it
        if os.path.exists(file_path):
            file_path_old = 'csv_files/' + file_name + '_OLD.csv'
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
