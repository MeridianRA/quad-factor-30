import csv
import math
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "csv_transformed" / "Nifty 50.csv"
OUTPUT_DIR = BASE_DIR / "data" / "backtest"
OUTPUT_FILE = OUTPUT_DIR / "benchmark_simulation.csv"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_FILE.relative_to(BASE_DIR)}"

INITIAL_INVESTMENT = 100_000.0

def read_prices():
    prices = []

    with INPUT_FILE.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames != ["date", "value"]:
            raise ValueError()

        previous_date = None
        for row in reader:
            current_date = date.fromisoformat(row["date"])
            value = float(row["value"])
            if not math.isfinite(value) or value <= 0:
                raise ValueError()
            if previous_date is not None and current_date <= previous_date:
                raise ValueError()

            prices.append((current_date, value))
            previous_date = current_date

    if not prices:
        raise ValueError()
    return prices

def calculate_simulation(prices):
    units = INITIAL_INVESTMENT / prices[0][1]

    for current_date, value in prices:
        portfolio_value = units * value
        yield {
            "date": current_date.isoformat(),
            "value": value,
            "portfolio_value": portfolio_value,
            "pnl_percent": (
                (portfolio_value - INITIAL_INVESTMENT)
                / INITIAL_INVESTMENT
                * 100
            ),
        }

def write_simulation(rows):
    fieldnames = ["date", "value", "portfolio_value", "pnl_percent"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "date": row["date"],
                    "value": f"{row['value']:.2f}",
                    "portfolio_value": f"{row['portfolio_value']:.2f}",
                    "pnl_percent": f"{row['pnl_percent']:.2f}",
                }
            )

def main():
    try:
        prices = read_prices()
        rows = list(calculate_simulation(prices))
        write_simulation(rows)
    except (csv.Error, OSError, TypeError, ValueError) as error:
        print(f"ERROR : {type(error).__name__}")
        return

    print(f"Simulated benchmark for {len(rows)} dates and saved to {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
