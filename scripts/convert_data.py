import csv
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

JSON_DIR = BASE_DIR / "data" / "json"
OUTPUT_DIR = BASE_DIR / "data" / "csv"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

def prepare_output_dir():
    if OUTPUT_DIR.exists():
        for child in OUTPUT_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"\nOutput directory exists : {OUTPUT_PATH_DISPLAY}")
        print("Cleared output directory")
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nCreated output directory : {OUTPUT_PATH_DISPLAY}")

def read_inputs():
    return sorted(JSON_DIR.glob("*.json"))

def convert_file(json_file):
    data = json.loads(json_file.read_text(encoding="utf-8"))
    records = data["data"] if isinstance(data, dict) else data
    if not isinstance(records, list) or not records:
        raise ValueError()

    with open(OUTPUT_DIR / f"{json_file.stem}.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

def process_file(json_file, label):
    try:
        convert_file(json_file)
    except (json.JSONDecodeError, ValueError, KeyError, TypeError, OSError) as error:
        print(f"{label}->  ERROR : {type(error).__name__}")
        return False
    print(f"{label}->  SUCCESS")
    return True

def main():
    try:
        inputs = read_inputs()
        if not inputs:
            raise ValueError()
        prepare_output_dir()
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    total = len(inputs)
    width = max(len(json_file.stem) for json_file in inputs) + 2
    print(f"\nConverting data for {total} input files ...\n")

    success = 0
    for json_file in inputs:
        label = f"{json_file.stem:<{width}}"
        success += process_file(json_file, label)

    print(f"\nConverted data for {success}/{total} input files")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
