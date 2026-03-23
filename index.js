const express = require("express");
const axios = require("axios");
const { rsi, impulseMACD } = require("./indicators");

const app = express();
app.use(express.json());

const TOKEN = process.env.TELEGRAM_TOKEN;
const CHAT_ID = process.env.CHAT_ID;

const SYMBOLS = [
  "AAPL","MSFT","NVDA","AMZN","GOOGL",
  "META","TSLA","JPM","XOM","KO"
];

// 📊 Fetch Yahoo
async function fetchData(symbol) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?range=1mo&interval=5m`;
  const res = await axios.get(url);

  const q = res.data.chart.result[0];
  const quote = q.indicators.quote[0];

  return {
    close: quote.close.filter(v => v),
    high: quote.high.filter(v => v),
    low: quote.low.filter(v => v)
  };
}

// 📩 Send Telegram
async function sendTelegram(text) {
  await axios.post(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
    chat_id: CHAT_ID,
    text
  });
}

// 🔥 Scan Function
async function runScan() {
  let msg = "📊 Watchlist Impulse MACD:\n";

  for (let s of SYMBOLS) {
    try {
      const data = await fetchData(s);

      const price = data.close.slice(-1)[0];
      const rsiVal = rsi(data.close);
      const md = impulseMACD(data).slice(-1)[0];

      let icon = "💀";
      if (md > 0) icon = "🟢";
      if (md < 0) icon = "🔴";

      msg += `${icon} ${s}: ${price.toFixed(2)} $, RSI: ${rsiVal.toFixed(2)}\n`;

    } catch (e) {
      console.log(s, "error");
    }
  }

  await sendTelegram(msg);
}

// ⏱️ Endpoint trigger
app.get("/scan", async (req, res) => {
  await runScan();
  res.send("OK");
});

app.listen(3000, () => console.log("Server running"));