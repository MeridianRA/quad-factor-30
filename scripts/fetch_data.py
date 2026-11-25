import json
import time
import shutil
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent

SYMBOL_FILE = "symbol.txt"
SYMBOL_PATH = BASE_DIR / "data" / "symbols" / SYMBOL_FILE
OUTPUT_DIR = BASE_DIR / "data" / "json"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_DIR.relative_to(BASE_DIR)}"

START_DATE = "01-Jan-2005"
END_DATE = "22-Nov-2026"
DATA_TYPES = ("TR", "HR")

REQUEST_SLEEP = 0.5

BASE_URL = "https://www.niftyindices.com"
API_URL = f"{BASE_URL}/Backpage/getHistoricaldataDBtoString"

HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json; charset=UTF-8",
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/market-data/advanced-charting",
    "x-requested-with": "XMLHttpRequest",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/156.0.0.0 Safari/537.36"
    ),
}

def read_symbols():
    return [
        s.strip()
        for s in SYMBOL_PATH.read_text(encoding="utf-8").splitlines()
        if s.strip()
    ]

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

def create_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(BASE_URL, timeout=10).raise_for_status()
    time.sleep(1)
    return session

def build_payload(symbol, data_type):
    cinfo = (
        f"{{'name':'{symbol}','startDate':'{START_DATE}','endDate':'{END_DATE}',"
        f"'historicaltype' :'2','DataType' : '{data_type}'}}"
    )
    return {"cinfo": cinfo}

def fetch_data(session, symbol):
    for data_type in DATA_TYPES:
        resp = session.post(API_URL, json=build_payload(symbol, data_type), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("data"):
            return data
    raise ValueError()

def process_symbol(session, symbol, label):
    try:
        data = fetch_data(session, symbol)
        (OUTPUT_DIR / f"{symbol}.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except (requests.RequestException, ValueError, OSError) as error:
        print(f"{label}->  ERROR : {type(error).__name__}")
        return False
    print(f"{label}->  SUCCESS")
    return True

def main():
    try:
        symbols = read_symbols()
        if not symbols:
            raise ValueError()
        session = create_session()
        prepare_output_dir()
    except Exception as error:
        print(f"ERROR : {type(error).__name__}")
        return

    total = len(symbols)
    width = max(len(s) for s in symbols) + 2
    print(f"\nDownloading data for {total} indices ...\n")

    success = 0
    for symbol in symbols:
        label = f"{symbol:<{width}}"
        success += process_symbol(session, symbol, label)
        time.sleep(REQUEST_SLEEP)

    print(f"\nDownloaded data for {success}/{total} indices")
    print(f"Saved to : {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
