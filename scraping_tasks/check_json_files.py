import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from useful_functions import ROOT_DIR


def check_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f)
        return None
    except UnicodeDecodeError as e:
        return f"UnicodeDecodeError: {e}"
    except json.JSONDecodeError as e:
        return f"JSONDecodeError: {e.msg} (line {e.lineno}, column {e.colno}, char {e.pos})"
    except OSError as e:
        return f"OSError: {e}"


def collect_json_files(*directories):
    json_files = []
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        for root, _, files in os.walk(directory):
            for file_name in files:
                if file_name.lower().endswith(".json"):
                    json_files.append(os.path.join(root, file_name))
    return sorted(json_files)


def main():
    json_dirs = [
        os.path.join(ROOT_DIR, "json_files"),
        os.path.join(ROOT_DIR, "OLD_json_files"),
    ]

    json_files = collect_json_files(*json_dirs)
    if not json_files:
        print("No se encontraron archivos .json")
        return 1

    invalid_files = []
    for file_path in json_files:
        error = check_json_file(file_path)
        if error:
            invalid_files.append((file_path, error))

    print(f"Revisados {len(json_files)} archivos JSON")
    print(f"Validos: {len(json_files) - len(invalid_files)}")
    print(f"Invalidos: {len(invalid_files)}")
    print()

    if invalid_files:
        print("Archivos JSON con errores:")
        print("-" * 80)
        for file_path, error in invalid_files:
            rel_path = os.path.relpath(file_path, ROOT_DIR)
            print(rel_path)
            print(f"  {error}")
            print()
        return 1

    print("Todos los archivos JSON son validos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
