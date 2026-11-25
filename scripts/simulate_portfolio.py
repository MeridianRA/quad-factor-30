import csv
import math
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_DIR = BASE_DIR / "data" / "csv_transformed"
OUTPUT_DIR = BASE_DIR / "data" / "backtest"
OUTPUT_FILE = OUTPUT_DIR / "portfolio_simulation.csv"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_FILE.relative_to(BASE_DIR)}"

INITIAL_INVESTMENT = 100_000.0

ALLOCATION = {
    "factors": (
        ("momentum", "Nifty200 Momentum 30", 0.25),
        ("quality", "Nifty200 Quality 30", 0.25),
        ("value", "Nifty200 Value 30", 0.25),
        ("low_volatility", "Nifty100 Low Volatility 30", 0.25),
    ),
}

def allocation_rows():
    return [
        security
        for asset_class in ALLOCATION.values()
        for security in asset_class
    ]

def read_prices(source_name):
    input_path = INPUT_DIR / f"{source_name}.csv"
    prices = {}

    with input_path.open("r", encoding="utf-8", newline="") as input_file:
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

            prices[current_date] = value
            previous_date = current_date

    if not prices:
        raise ValueError()
    return prices

def load_price_data():
    source_names = {source_name for _, source_name, _ in allocation_rows()}
    return {
        source_name: read_prices(source_name)
        for source_name in sorted(source_names)
    }

def validate_allocation():
    total_weight = sum(weight for _, _, weight in allocation_rows())
    if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
        raise ValueError()

def calculate_simulation(price_data):
    start_date = max(min(prices) for prices in price_data.values())
    simulation_dates = sorted(
        simulation_date
        for simulation_date in {
            current_date
            for prices in price_data.values()
            for current_date in prices
        }
        if simulation_date >= start_date
    )

    units = {}
    for security_name, source_name, weight in allocation_rows():
        starting_price = max(
            (
                (current_date, value)
                for current_date, value in price_data[source_name].items()
                if current_date <= start_date
            ),
            key=lambda item: item[0],
        )[1]
        units[security_name] = INITIAL_INVESTMENT * weight / starting_price

    price_indexes = {
        source_name: iter(sorted(prices.items()))
        for source_name, prices in price_data.items()
    }
    current_values = {}
    pending_values = {
        source_name: next(rows, None)
        for source_name, rows in price_indexes.items()
    }

    for simulation_date in simulation_dates:
        for source_name, next_value in tuple(pending_values.items()):
            while next_value is not None and next_value[0] <= simulation_date:
                current_values[source_name] = next_value[1]
                next_value = next(price_indexes[source_name], None)
            pending_values[source_name] = next_value

        security_values = {
            security_name: units[security_name] * current_values[source_name]
            for security_name, source_name, _ in allocation_rows()
        }
        portfolio_value = sum(security_values.values())

        row = {"date": simulation_date.isoformat()}
        row.update(
            (f"{security_name}_value", security_values[security_name])
            for security_name, _, _ in allocation_rows()
        )
        row["portfolio_value"] = portfolio_value
        row["pnl_percent"] = (
            (portfolio_value - INITIAL_INVESTMENT) / INITIAL_INVESTMENT * 100
        )
        yield row

def write_simulation(rows):
    fieldnames = ["date"]
    fieldnames.extend(
        f"{security_name}_value"
        for security_name, _, _ in allocation_rows()
    )
    fieldnames.extend(("portfolio_value", "pnl_percent"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    column: (
                        value
                        if column == "date"
                        else f"{value:.2f}"
                    )
                    for column, value in row.items()
                }
            )

def main():
    try:
        validate_allocation()
        price_data = load_price_data()
        rows = list(calculate_simulation(price_data))
        if not rows:
            raise ValueError()
        write_simulation(rows)
    except (csv.Error, KeyError, OSError, TypeError, ValueError) as error:
        print(f"ERROR : {type(error).__name__}")
        return

    print(f"Simulated portfolio for {len(rows)} dates and saved to {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
