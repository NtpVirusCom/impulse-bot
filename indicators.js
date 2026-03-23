function average(arr) {
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function ema(values, period) {
  let k = 2 / (period + 1);
  let result = [];
  let prev = values[0];

  values.forEach((v, i) => {
    if (i === 0) result.push(v);
    else {
      prev = v * k + prev * (1 - k);
      result.push(prev);
    }
  });

  return result;
}

function zlema(values, period) {
  const ema1 = ema(values, period);
  const ema2 = ema(ema1, period);
  return ema1.map((v, i) => v + (v - ema2[i]));
}

function smma(values, period) {
  let result = [];
  let prev;

  values.forEach((v, i) => {
    if (i < period) result.push(null);
    else if (i === period) {
      const sma = average(values.slice(0, period));
      prev = sma;
      result.push(sma);
    } else {
      const val = (prev * (period - 1) + v) / period;
      result.push(val);
      prev = val;
    }
  });

  return result;
}

function rsi(values, period = 14) {
  let gains = [], losses = [];

  for (let i = 1; i < values.length; i++) {
    const diff = values[i] - values[i - 1];
    gains.push(diff > 0 ? diff : 0);
    losses.push(diff < 0 ? Math.abs(diff) : 0);
  }

  const avgGain = average(gains.slice(-period));
  const avgLoss = average(losses.slice(-period));

  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

function impulseMACD(data) {
  const { close, high, low } = data;
  const hlc3 = close.map((c, i) => (high[i] + low[i] + c) / 3);

  const hi = smma(high, 34);
  const lo = smma(low, 34);
  const mi = zlema(hlc3, 34);

  let md = [];

  for (let i = 0; i < close.length; i++) {
    if (mi[i] > hi[i]) md.push(mi[i] - hi[i]);
    else if (mi[i] < lo[i]) md.push(mi[i] - lo[i]);
    else md.push(0);
  }

  return md;
}

module.exports = { rsi, impulseMACD };