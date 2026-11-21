#!/usr/bin/env python3
"""Local endpoints for chart regeneration and stop-loss estimates."""

import json
import re
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import Request, urlopen

ATR_WINDOW = 15
PIVOT_WINDOW = 2
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9.^=_-]{1,20}$")


def estimate_stop_loss(candles, atr_window=ATR_WINDOW, pivot_window=PIVOT_WINDOW):
    """Estimate a stop below the latest confirmed pivot high after the latest pivot low."""
    if len(candles) < atr_window + 2 * pivot_window + 1:
        raise ValueError(
            "Not enough weekly data to calculate ATR and confirmed swing points."
        )

    true_ranges = []
    for index, candle in enumerate(candles):
        high = candle["high"]
        low = candle["low"]
        previous_close = candles[index - 1]["close"] if index else candle["close"]
        true_ranges.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )

    pivot_lows = _find_confirmed_pivots(candles, "low", pivot_window, is_high=False)
    if not pivot_lows:
        raise ValueError("No confirmed weekly swing low was found.")

    latest_pivot_low = pivot_lows[-1]
    pivot_highs = _find_confirmed_pivots(
        candles,
        "high",
        pivot_window,
        is_high=True,
        start_index=latest_pivot_low + 1,
    )
    if not pivot_highs:
        raise ValueError(
            "No confirmed swing high was found after the latest swing low."
        )

    swing_index = pivot_highs[-1]
    if swing_index + 1 < atr_window:
        raise ValueError(
            "Not enough weekly history at the swing high to calculate ATR."
        )

    atr = sum(true_ranges[swing_index - atr_window + 1 : swing_index + 1]) / atr_window
    swing_high = candles[swing_index]
    return {
        "swing_high_date": swing_high["date"],
        "swing_high": round(swing_high["high"], 2),
        "atr_window": atr_window,
        "atr": round(atr, 2),
        "estimates": [
            {
                "multiplier": multiplier,
                "atr_distance": round(multiplier * atr, 2),
                "stop_loss": round(swing_high["high"] - multiplier * atr, 2),
            }
            for multiplier in (1.5, 2.5, 3.5)
        ],
        "latest_close": round(candles[-1]["close"], 2),
        "latest_date": candles[-1]["date"],
    }


def _find_confirmed_pivots(candles, field, pivot_window, is_high, start_index=None):
    start_index = max(pivot_window, start_index or 0)
    pivots = []
    for index in range(start_index, len(candles) - pivot_window):
        neighbors = list(range(index - pivot_window, index)) + list(
            range(index + 1, index + pivot_window + 1)
        )
        price = candles[index][field]
        if all(
            price > candles[neighbor][field]
            if is_high
            else price < candles[neighbor][field]
            for neighbor in neighbors
        ):
            pivots.append(index)
    return pivots


def estimate_daily_stop_loss(candles, pivot_window=PIVOT_WINDOW):
    """Estimate a stop one percent below the latest confirmed daily swing low."""
    if len(candles) < 2 * pivot_window + 1:
        raise ValueError("Not enough daily data to confirm a swing low.")
    pivot_lows = _find_confirmed_pivots(candles, "low", pivot_window, is_high=False)
    if not pivot_lows:
        raise ValueError("No confirmed daily swing low was found.")

    swing_low = candles[pivot_lows[-1]]
    return {
        "swing_low_date": swing_low["date"],
        "swing_low": round(swing_low["low"], 2),
        "percent_below": 1.0,
        "stop_distance": round(swing_low["low"] * 0.01, 2),
        "stop_loss": round(swing_low["low"] * 0.99, 2),
        "latest_close": round(candles[-1]["close"], 2),
        "latest_date": candles[-1]["date"],
    }


def estimate_daily_buy_point(candles, pivot_window=PIVOT_WINDOW):
    """Estimate the latest confirmed daily swing high (a buy point)."""
    if len(candles) < 2 * pivot_window + 1:
        raise ValueError("Not enough daily data to confirm a swing high.")
    pivot_highs = _find_confirmed_pivots(candles, "high", pivot_window, is_high=True)
    if not pivot_highs:
        raise ValueError("No confirmed daily swing high was found.")

    swing_high = candles[pivot_highs[-1]]
    return {
        "swing_high_date": swing_high["date"],
        "swing_high": round(swing_high["high"], 2),
        "pivot_window": pivot_window,
        "latest_close": round(candles[-1]["close"], 2),
        "latest_date": candles[-1]["date"],
    }


def _fetch_candles(symbol, period, interval, frequency):
    """Fetch split/dividend-adjusted candles from Yahoo Finance."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{quote(symbol, safe='')}?range={period}&interval={interval}&events=div%2Csplits"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Unable to retrieve {frequency} data for {symbol}: {error}"
        ) from error

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise ValueError(
            chart["error"].get("description", "The data provider returned an error.")
        )
    results = chart.get("result") or []
    if not results:
        raise ValueError(f"No {frequency} data found for {symbol}.")

    result = results[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators", {})
    quotes = (indicators.get("quote") or [{}])[0]
    adjusted_closes = (indicators.get("adjclose") or [{}])[0].get("adjclose") or []
    highs = quotes.get("high") or []
    lows = quotes.get("low") or []
    closes = quotes.get("close") or []

    candles = []
    for index, timestamp in enumerate(timestamps):
        if index >= min(len(highs), len(lows), len(closes)):
            break
        high, low, close = highs[index], lows[index], closes[index]
        if high is None or low is None or close is None:
            continue
        adjusted_close = (
            adjusted_closes[index] if index < len(adjusted_closes) else None
        )
        adjustment = adjusted_close / close if adjusted_close and close else 1.0
        candles.append(
            {
                "date": datetime.fromtimestamp(timestamp, timezone.utc)
                .date()
                .isoformat(),
                "high": high * adjustment,
                "low": low * adjustment,
                "close": close * adjustment,
            }
        )
    if not candles:
        raise ValueError(f"No usable {frequency} candles found for {symbol}.")
    return candles


def fetch_weekly_candles(symbol):
    """Fetch five years of weekly candles."""
    return _fetch_candles(symbol, "5y", "1wk", "weekly")


def fetch_daily_candles(symbol):
    """Fetch one year of daily candles."""
    return _fetch_candles(symbol, "1y", "1d", "daily")


class Handler(BaseHTTPRequestHandler):
    def _respond_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _run(self):
        r = subprocess.run(
            ["python3", "/app/generate_chart_index.py"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        r2 = subprocess.run(
            ["python3", "/app/render_md.py"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        ok = r.returncode == 0 and r2.returncode == 0
        out = (r.stdout or "") + (r2.stdout or "")
        err = (r.stderr or "") + (r2.stderr or "")
        return ok, out, err

    def _respond(self, ok, out, err):
        body = json.dumps({"ok": ok, "output": out, "error": err}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self):
        if (
            self.path.rstrip("/") == "/regenerate"
            or self.path.rstrip("/") == "/regenerate"
        ):
            ok, out, err = self._run()
            self._respond(ok, out, err)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_GET(self):
        request = urlsplit(self.path)
        if request.path in ("/api/stop-loss", "/api/daily-stop-loss", "/api/buy-point"):
            symbol = parse_qs(request.query).get("symbol", [""])[0].strip().upper()
            if not SYMBOL_PATTERN.fullmatch(symbol):
                self._respond_json(400, {"error": "Enter a valid stock ticker symbol."})
                return
            is_daily = request.path in ("/api/daily-stop-loss", "/api/buy-point")
            try:
                candles = (
                    fetch_daily_candles(symbol)
                    if is_daily
                    else fetch_weekly_candles(symbol)
                )
            except ValueError as error:
                self._respond_json(502, {"error": str(error)})
                return
            try:
                if request.path == "/api/buy-point":
                    estimate = estimate_daily_buy_point(candles)
                elif is_daily:
                    estimate = estimate_daily_stop_loss(candles)
                else:
                    estimate = estimate_stop_loss(candles)
            except ValueError as error:
                self._respond_json(422, {"error": str(error)})
                return
            self._respond_json(200, {"symbol": symbol, **estimate})
            return
        self._handle()

    def do_POST(self):
        self._handle()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
