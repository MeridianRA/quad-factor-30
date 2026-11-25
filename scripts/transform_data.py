import csv
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_DIR = BASE_DIR / "data" / "csv"
OUTPUT_DIR = BASE_DIR / "data" / "csv_transformed"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

LAYOUTS = (
    ("HistoricalDate", "%d %b %Y", "CLOSE"),
    ("TRIDate", "%d %b %Y", "Total Returns Index"),
    ("mTIMESTAMP", "%d-%b-%Y", "CH_CLOSING_PRICE"),
)

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
    return sorted(INPUT_DIR.glob("*.csv"))

def transform_file(input_file):
    with open(input_file, encoding="utf-8", newline="") as f:
        records = list(csv.DictReader(f))
    if not records:
        raise ValueError()

    date_column, date_format, value_column = next(
        layout for layout in LAYOUTS if layout[0] in records[0] and layout[2] in records[0]
    )
    rows = [
        {
            "date": datetime.strptime(record[date_column], date_format).date().isoformat(),
            "value": float(record[value_column]),
        }
        for record in records
    ]
    rows.sort(key=lambda r: r["date"])

    with open(OUTPUT_DIR / input_file.name, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "value"])
        writer.writeheader()
        writer.writerows(rows)

def process_file(input_file, label):
    try:
        transform_file(input_file)
    except (StopIteration, UnicodeDecodeError, ValueError, KeyError, TypeError, OSError) as error:
        print(f"{label}->  ERROR : {type(error).__name__}")
        return False
    print(f"{label}->  SUCCESS")
    return True

def main():
    try:
        input_files = read_inputs()
        if not input_files:
            raise ValueError()
        prepare_output_dir()
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    total = len(input_files)
    width = max(len(f.stem) for f in input_files) + 2
    print(f"\nTransforming data for {total} input files ...\n")

    success = 0
    for input_file in input_files:
        label = f"{input_file.stem:<{width}}"
        success += process_file(input_file, label)

    print(f"\nTransformed data for {success}/{total} input files")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
