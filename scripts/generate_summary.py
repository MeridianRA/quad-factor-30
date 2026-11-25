import csv
import math
from bisect import bisect_right
from calendar import monthrange
from datetime import date
from pathlib import Path
from statistics import StatisticsError, correlation, mean, stdev

BASE_DIR = Path(__file__).resolve().parent.parent

BACKTEST_DIR = BASE_DIR / "data" / "backtest"
PORTFOLIO_FILE = BACKTEST_DIR / "portfolio_simulation.csv"
NIFTY_50_FILE = BACKTEST_DIR / "benchmark_simulation.csv"
OUTPUT_FILE = BACKTEST_DIR / "summary.csv"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_FILE.relative_to(BASE_DIR)}"

TRADING_DAYS_PER_YEAR = 252

PARAMETERS = (
    "cagr",
    "volatility",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "correlation",
    "rolling_returns_1y",
    "rolling_returns_3y",
    "rolling_returns_5y",
    "rolling_returns_10y",
    "positive_months",
    "positive_months_pct",
    "portfolio_value",
)

def read_values(input_path):
    values = {}

    with input_path.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        required_columns = {"date", "portfolio_value"}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise ValueError()

        previous_date = None
        for row in reader:
            current_date = date.fromisoformat(row["date"])
            value = float(row["portfolio_value"])
            if not math.isfinite(value) or value <= 0:
                raise ValueError()
            if previous_date is not None and current_date <= previous_date:
                raise ValueError()

            values[current_date] = value
            previous_date = current_date

    if len(values) < 2:
        raise ValueError()
    return values

def align_values(portfolio_values, nifty_50_values):
    shared_dates = sorted(portfolio_values.keys() & nifty_50_values.keys())
    if len(shared_dates) < 2:
        raise ValueError()
    return (
        shared_dates,
        [portfolio_values[current_date] for current_date in shared_dates],
        [nifty_50_values[current_date] for current_date in shared_dates],
    )

def daily_returns(values):
    return [
        values[index] / values[index - 1] - 1
        for index in range(1, len(values))
    ]

def annualized_return(values, dates):
    years = (dates[-1] - dates[0]).days / 365.25
    if years <= 0:
        raise ValueError()
    return (values[-1] / values[0]) ** (1 / years) - 1

def volatility(returns):
    return stdev(returns) * math.sqrt(TRADING_DAYS_PER_YEAR)

def sharpe_ratio(returns):
    standard_deviation = stdev(returns)
    if standard_deviation == 0:
        return 0.0
    return (
        mean(returns)
        / standard_deviation
        * math.sqrt(TRADING_DAYS_PER_YEAR)
    )

def sortino_ratio(returns):
    downside_deviation = math.sqrt(
        sum(min(value, 0.0) ** 2 for value in returns) / len(returns)
    )
    if downside_deviation == 0:
        return 0.0
    return (
        mean(returns)
        / downside_deviation
        * math.sqrt(TRADING_DAYS_PER_YEAR)
    )

def max_drawdown(values):
    peak = values[0]
    largest_drawdown = 0.0

    for value in values:
        peak = max(peak, value)
        largest_drawdown = min(largest_drawdown, value / peak - 1)
    return largest_drawdown

def subtract_years(current_date, years):
    replacement_day = min(
        current_date.day,
        monthrange(current_date.year - years, current_date.month)[1],
    )
    return current_date.replace(
        year=current_date.year - years,
        day=replacement_day,
    )

def rolling_return(dates, values, years):
    target_date = subtract_years(dates[-1], years)
    start_index = bisect_right(dates, target_date) - 1
    if start_index < 0:
        raise ValueError()

    elapsed_years = (dates[-1] - dates[start_index]).days / 365.25
    if elapsed_years <= 0:
        raise ValueError()
    return (values[-1] / values[start_index]) ** (1 / elapsed_years) - 1

def monthly_returns(dates, values):
    month_end_values = {}
    for current_date, value in zip(dates, values):
        month_end_values[(current_date.year, current_date.month)] = value

    ordered_values = [
        value
        for _, value in sorted(month_end_values.items())
    ]
    return daily_returns(ordered_values)

def series_summary(dates, values):
    returns = daily_returns(values)
    month_returns = monthly_returns(dates, values)
    positive_month_count = sum(value > 0 for value in month_returns)

    return {
        "cagr": annualized_return(values, dates) * 100,
        "volatility": volatility(returns) * 100,
        "sharpe_ratio": sharpe_ratio(returns),
        "sortino_ratio": sortino_ratio(returns),
        "max_drawdown": max_drawdown(values) * 100,
        "rolling_returns_1y": rolling_return(dates, values, 1) * 100,
        "rolling_returns_3y": rolling_return(dates, values, 3) * 100,
        "rolling_returns_5y": rolling_return(dates, values, 5) * 100,
        "rolling_returns_10y": rolling_return(dates, values, 10) * 100,
        "positive_months": positive_month_count,
        "positive_months_pct": (
            positive_month_count / len(month_returns) * 100
        ),
        "portfolio_value": values[-1],
    }

def generate_summary():
    portfolio_values_by_date = read_values(PORTFOLIO_FILE)
    nifty_50_values_by_date = read_values(NIFTY_50_FILE)
    dates, portfolio_values, nifty_50_values = align_values(
        portfolio_values_by_date,
        nifty_50_values_by_date,
    )

    portfolio_summary = series_summary(dates, portfolio_values)
    nifty_50_summary = series_summary(dates, nifty_50_values)

    paired_correlation = correlation(
        daily_returns(portfolio_values),
        daily_returns(nifty_50_values),
    )
    portfolio_summary["correlation"] = paired_correlation
    nifty_50_summary["correlation"] = 1.0

    return [
        {
            "parameter": parameter,
            "portfolio": portfolio_summary[parameter],
            "nifty_50": nifty_50_summary[parameter],
        }
        for parameter in PARAMETERS
    ]

def write_summary(rows):
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=["parameter", "portfolio", "nifty_50"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "parameter": row["parameter"],
                    "portfolio": f"{row['portfolio']:.2f}",
                    "nifty_50": f"{row['nifty_50']:.2f}",
                }
            )

def main():
    try:
        rows = generate_summary()
        write_summary(rows)
    except (csv.Error, KeyError, OSError, StatisticsError, TypeError, ValueError) as error:
        print(f"ERROR : {type(error).__name__}")
        return

    print(f"Generated summary for {len(rows)} parameters and saved to {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
