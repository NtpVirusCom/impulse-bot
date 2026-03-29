import yfinance as yf
import pandas as pd
import numpy as np
import requests

# ==============================
# CONFIG
# ==============================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ==============================
# LOAD SYMBOLS
# ==============================
def get_sp500():
    url = "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv"
    df = pd.read_csv(url)

    col = "Symbol" if "Symbol" in df.columns else df.columns[0]

    return (
        df[col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.replace(".", "-", regex=False)
        .unique()
        .tolist()
    )


def get_nasdaq100():
    url = "https://raw.githubusercontent.com/Gary-Strauss/NASDAQ100_Constituents/master/data/nasdaq100_constituents.csv"
    df = pd.read_csv(url)

    col = "Ticker" if "Ticker" in df.columns else df.columns[0]

    return (
        df[col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.replace(".", "-", regex=False)
        .unique()
        .tolist()
    )


def get_symbols():
    symbols = list(set(get_sp500() + get_nasdaq100()))

    blacklist = {"BF-B"}
    symbols = [s for s in symbols if s not in blacklist]

    symbols.sort()
    print(f"Total symbols: {len(symbols)}")
    return symbols


# ==============================
# RSI
# ==============================
def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


# ==============================
# Impulse MACD
# ==============================
def calculate_impulse(df):
    lengthMA = 34
    lengthSignal = 9

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    src = (high + low + close) / 3

    # SMMA
    smma_high = high.ewm(alpha=1/lengthMA, adjust=False).mean()
    smma_low = low.ewm(alpha=1/lengthMA, adjust=False).mean()

    # ZLEMA
    ema1 = src.ewm(span=lengthMA, adjust=False).mean()
    ema2 = ema1.ewm(span=lengthMA, adjust=False).mean()
    mi = ema1 + (ema1 - ema2)

    # MD
    md = np.where(
        mi > smma_high, mi - smma_high,
        np.where(mi < smma_low, mi - smma_low, 0)
    )
    md = pd.Series(md, index=df.index)

    # Signal line
    sb = md.rolling(lengthSignal).mean()

    # Compare
    cmp = np.where(md > sb, 1,
          np.where(md < sb, -1, 0))
    cmp = pd.Series(cmp, index=df.index)

    # Signal detect
    signal = []
    for i in range(len(cmp)):
        if i == 0 or pd.isna(cmp.iloc[i]) or pd.isna(cmp.iloc[i-1]):
            signal.append("-")
        elif cmp.iloc[i] != cmp.iloc[i-1]:
            if cmp.iloc[i] == 1:
                signal.append("BUY")
            elif cmp.iloc[i] == -1:
                signal.append("SELL")
            else:
                signal.append("-")
        else:
            signal.append("-")

    df["MD"] = md
    df["SB"] = sb
    df["CMP"] = cmp
    df["Signal"] = signal
    df["RSI"] = calculate_rsi(close)

    return df


# ==============================
# TELEGRAM
# ==============================
def send_telegram(messages):
    batch_size = 10
    total_batches = (len(messages) + batch_size - 1) // batch_size

    for i in range(0, len(messages), batch_size):
        batch = messages[i:i+batch_size]
        batch_num = i // batch_size + 1

        #text = f"📊 *Watchlist Impulse MACD ({batch_num}/{total_batches}):*\n\n"
        #text += "\n\n".join(batch)

        text = f"📊 *Watchlist Impulse MACD ({batch_num}/{total_batches}):*\n"
        text += "\n".join(batch)

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            }
        )


# ==============================
# MAIN
# ==============================
def main():
    symbols = get_symbols()

    print("Downloading data...")
    data = yf.download(
        symbols,
        period="3y",
        interval="1d",
        group_by="ticker",
        threads=True
    )

    messages = []

    for ticker in symbols:
        try:
            df = data[ticker].dropna()

            if len(df) < 50:
                continue

            df = calculate_impulse(df)

            last = df.iloc[-1]
            prev = df.iloc[-2]

            signal = last["Signal"]
            rsi = last["RSI"]
            price = round(last["Close"], 2)

            md_val = last["MD"]
            sb_val = last["SB"]
            cmp_val = last["CMP"]
            prev_cmp = prev["CMP"]

            # ===== SIGNAL UPGRADE =====
            if signal == "BUY":
                if md_val < 0:
                    signal = "Strong BUY"
                    icon = "🔥"
                else:
                    icon = "😍"

            elif signal == "SELL":
                if md_val > 0:
                    signal = "Strong SELL"
                    icon = "☠️"
                else:
                    icon = "💀"
            else:
                continue

            arrow = "▲" if rsi > prev["RSI"] else "▼"

            #msg = (
            #    f"{icon} *{ticker}*: {price} $\n"
            #    f"Type: {signal}\n"
            #    f"RSI: {rsi:.2f} {arrow}\n"
            #    f"MD: {md_val:.4f}\n"
            #    f"Signal: {sb_val:.4f}\n"
            #    f"CMP: {int(cmp_val)}\n"
            #    f"Cross: {int(prev_cmp)} → {int(cmp_val)}"
            #)

            msg = f"{icon} *{ticker}*: {price} $, RSI: {rsi:.2f} {arrow}"

            messages.append(msg)

        except Exception as e:
            print(f"Error {ticker}: {e}")

    if messages:
        send_telegram(messages)

    print("Done.")


# ==============================
if __name__ == "__main__":
    main()
