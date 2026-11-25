import csv
import html
import math
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

BACKTEST_DIR = BASE_DIR / "data" / "backtest"
PORTFOLIO_FILE = BACKTEST_DIR / "portfolio_simulation.csv"
NIFTY_50_FILE = BACKTEST_DIR / "benchmark_simulation.csv"
OUTPUT_FILE = BACKTEST_DIR / "curves.svg"
OUTPUT_PATH_DISPLAY = f"{BASE_DIR.name}/{OUTPUT_FILE.relative_to(BASE_DIR)}"

SVG_WIDTH = 1280
SVG_HEIGHT = 720
PLOT_LEFT = 95
PLOT_RIGHT = 1235
EQUITY_TOP = 96
EQUITY_BOTTOM = 358
DRAWDOWN_TOP = 423
DRAWDOWN_BOTTOM = 685

COLORS = {
    "portfolio": "#2563eb",
    "nifty_50": "#dc2626",
}

def read_values(input_path):
    values = {}

    with input_path.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames is None or not {
            "date",
            "portfolio_value",
        }.issubset(reader.fieldnames):
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
    dates = sorted(portfolio_values.keys() & nifty_50_values.keys())
    if len(dates) < 2:
        raise ValueError()
    return {
        "dates": dates,
        "portfolio": [portfolio_values[current_date] for current_date in dates],
        "nifty_50": [nifty_50_values[current_date] for current_date in dates],
    }

def calculate_drawdowns(values):
    peak = values[0]
    drawdowns = []
    for value in values:
        peak = max(peak, value)
        drawdowns.append((value / peak - 1) * 100)
    return drawdowns

def scale_linear(value, minimum, maximum, output_minimum, output_maximum):
    if maximum == minimum:
        return (output_minimum + output_maximum) / 2
    position = (value - minimum) / (maximum - minimum)
    return output_minimum + position * (output_maximum - output_minimum)

def line_path(values, minimum, maximum, dates, top, bottom):
    first_date = dates[0]
    date_span = (dates[-1] - first_date).days
    points = []

    for current_date, value in zip(dates, values):
        x = (
            PLOT_LEFT
            + (current_date - first_date).days / date_span * (PLOT_RIGHT - PLOT_LEFT)
        )
        y = scale_linear(value, minimum, maximum, bottom, top)
        points.append(f"{x:.2f},{y:.2f}")
    return "M " + " L ".join(points)

def nice_step(span, target_lines=5):
    rough_step = span / target_lines
    magnitude = 10 ** math.floor(math.log10(rough_step))
    normalized = rough_step / magnitude
    if normalized <= 1:
        return magnitude
    if normalized <= 2:
        return 2 * magnitude
    if normalized <= 5:
        return 5 * magnitude
    return 10 * magnitude

def axis_values(minimum, maximum):
    if minimum == maximum:
        padding = max(abs(minimum) * 0.05, 1.0)
        minimum -= padding
        maximum += padding

    step = nice_step(maximum - minimum)
    start = math.floor(minimum / step) * step
    end = math.ceil(maximum / step) * step
    values = []
    current = start
    while current <= end + step / 2:
        values.append(current)
        current += step
    return start, end, values

def text_element(x, y, content, extra_attributes=""):
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" '
        f'{extra_attributes}>{html.escape(str(content))}</text>'
    )

def horizontal_axis(dates):
    elements = []
    first_date = dates[0]
    date_span = (dates[-1] - first_date).days
    ticks = [
        (first_date, "Apr 2005"),
        (date(2007, 1, 1), "2007"),
        (date(2009, 1, 1), "2009"),
        (date(2011, 1, 1), "2011"),
        (date(2013, 1, 1), "2013"),
        (date(2015, 1, 1), "2015"),
        (date(2017, 1, 1), "2017"),
        (date(2019, 1, 1), "2019"),
        (date(2021, 1, 1), "2021"),
        (date(2023, 1, 1), "2023"),
        (date(2025, 1, 1), "2025"),
        (dates[-1], "Nov 2026"),
    ]
    for tick_date, label in ticks:
        x = (
            PLOT_LEFT
            + (tick_date - first_date).days
            / date_span
            * (PLOT_RIGHT - PLOT_LEFT)
        )
        elements.append(
            text_element(
                x,
                DRAWDOWN_BOTTOM + 28,
                label,
                'text-anchor="middle" class="axis-label"',
            )
        )
    return "\n".join(elements)

def year_start_lines(dates, top, bottom):
    elements = []
    first_date = dates[0]
    date_span = (dates[-1] - first_date).days

    first_year = (
        first_date.year
        if first_date.month == 1 and first_date.day == 1
        else first_date.year + 1
    )
    for year in range(first_year, dates[-1].year + 1):
        year_start = date(year, 1, 1)
        x = (
            PLOT_LEFT
            + (year_start - first_date).days
            / date_span
            * (PLOT_RIGHT - PLOT_LEFT)
        )
        elements.append(
            f'<line x1="{x:.2f}" y1="{top}" '
            f'x2="{x:.2f}" y2="{bottom}" class="year-line"/>'
        )
    return "\n".join(elements)

def plot_panel(
    dates,
    series,
    top,
    bottom,
    title,
    value_formatter,
    fixed_axis=None,
):
    all_values = [
        value
        for values in series.values()
        for value in values
    ]
    if fixed_axis is None:
        minimum, maximum, tick_values = axis_values(
            min(all_values),
            max(all_values),
        )
    else:
        minimum, maximum, tick_values = fixed_axis
    title_x = 30
    title_y = (top + bottom) / 2
    elements = [
        text_element(
            title_x,
            title_y,
            title,
            f'transform="rotate(-90 {title_x} {title_y})" '
            'text-anchor="middle" class="panel-title"',
        )
    ]
    elements.append(year_start_lines(dates, top, bottom))

    for tick_value in tick_values:
        y = scale_linear(tick_value, minimum, maximum, bottom, top)
        elements.append(
            f'<line x1="{PLOT_LEFT}" y1="{y:.2f}" '
            f'x2="{PLOT_RIGHT}" y2="{y:.2f}" class="grid-line"/>'
        )
        elements.append(
            text_element(
                PLOT_LEFT - 12,
                y + 4,
                value_formatter(tick_value),
                'text-anchor="end" class="axis-label"',
            )
        )

    elements.append(
        f'<line x1="{PLOT_LEFT}" y1="{bottom}" '
        f'x2="{PLOT_RIGHT}" y2="{bottom}" class="axis-line"/>'
    )
    for name, values in series.items():
        path = line_path(values, minimum, maximum, dates, top, bottom)
        elements.append(
            f'<path d="{path}" fill="none" stroke="{COLORS[name]}" '
            'stroke-width="1.5" stroke-linejoin="round" '
            'stroke-linecap="round"/>'
        )
    return "\n".join(elements)

def build_svg(data):
    dates = data["dates"]
    drawdowns = {
        name: calculate_drawdowns(data[name])
        for name in ("portfolio", "nifty_50")
    }
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
    width="{SVG_WIDTH}" height="{SVG_HEIGHT}"
    viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}"
    role="img" aria-labelledby="title description">
  <title id="title">Portfolio and Nifty 50 equity and drawdown curves</title>
  <desc id="description">Comparison of buy-and-hold portfolio values and percentage drawdowns.</desc>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #334155; }}
    .heading {{ font-size: 20px; font-weight: 350; fill: #0f172a; }}
    .panel-title {{ font-size: 16px; font-weight: 500; fill: #1e293b; }}
    .axis-label {{ font-size: 12px; fill: #64748b; }}
    .legend {{ font-size: 14px; fill: #334155; }}
    .grid-line {{ stroke: #e2e8f0; stroke-width: 1; }}
    .year-line {{ stroke: #e2e8f0; stroke-width: 1; }}
    .axis-line {{ stroke: #94a3b8; stroke-width: 1; }}
  </style>
  <rect width="{SVG_WIDTH}" height="{SVG_HEIGHT}" fill="#ffffff"/>
  {text_element(
      PLOT_LEFT,
      42,
      "Portfolio & Benchmark Performance Curve",
      'class="heading"',
  )}
  <line x1="730" y1="28" x2="758" y2="28" stroke="{COLORS["portfolio"]}" stroke-width="4"/>
  {text_element(770, 33, "Portfolio", 'class="legend"')}
  <line x1="880" y1="28" x2="908" y2="28" stroke="{COLORS["nifty_50"]}" stroke-width="4"/>
  {text_element(920, 33, "Nifty 50", 'class="legend"')}
  {plot_panel(
      dates,
      {"portfolio": data["portfolio"], "nifty_50": data["nifty_50"]},
      EQUITY_TOP,
      EQUITY_BOTTOM,
      "Equity Curve (INR)",
      lambda value: "0" if value == 0 else f"{value / 100000:.0f}L",
      (0, 4_000_000, [0, 1_000_000, 2_000_000, 3_000_000, 4_000_000]),
  )}
  {plot_panel(
      dates,
      drawdowns,
      DRAWDOWN_TOP,
      DRAWDOWN_BOTTOM,
      "Drawdown Curve (%)",
      lambda value: f"{value:.0f}%",
  )}
  {horizontal_axis(dates)}
</svg>
"""

def main():
    try:
        data = align_values(read_values(PORTFOLIO_FILE), read_values(NIFTY_50_FILE))
        svg = build_svg(data)
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(svg, encoding="utf-8")
    except (csv.Error, OSError, TypeError, ValueError) as error:
        print(f"ERROR : {type(error).__name__}")
        return

    print(f"Generated equity and drawdown curves for {len(data['dates'])} dates and saved to {OUTPUT_PATH_DISPLAY}")

if __name__ == "__main__":
    main()
