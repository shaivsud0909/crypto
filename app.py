from flask import Flask, request, render_template_string
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib as p
import io
import base64
import pytz

p.use('Agg')  # Use non-GUI backend for web servers

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def render_chart():
    symbol = "BTC-USD"  # default
    image_base64 = None
    error = None

    if request.method == "POST":
        coin = request.form.get("coin", "BTC")
        symbol = 'BTC-USD' if coin == 'BTC' else 'ETH-USD'

        # Fetch crypto data
        crypto = yf.Ticker(symbol)
        live_data = crypto.history(period="30d", interval="1d")

        if live_data.empty:
            error = "No data found for selected coin."
        else:
            # Convert timezone
            live_data.index = live_data.index.tz_convert("Asia/Kolkata")

            # Add EMAs
            live_data['8_day_MA'] = live_data['Close'].ewm(span=8, adjust=False).mean()     # Exponentially Weighted Moving statistics. It's used to calculate metrics like moving averages
            live_data['16_day_MA'] = live_data['Close'].ewm(span=16, adjust=False).mean()

            # Support/resistance
            supports = []
            resistances = []
            for i in range(1, len(live_data) - 1):
                prev = live_data['Close'].iloc[i - 1]
                curr = live_data['Close'].iloc[i]
                next_ = live_data['Close'].iloc[i + 1]

                if curr < prev and curr < next_:
                    supports.append((live_data.index[i], curr))
                elif curr > prev and curr > next_:
                    resistances.append((live_data.index[i], curr))

            # Trend check
            latest_price = live_data['Close'].iloc[-1]
            ema_8 = live_data['8_day_MA'].iloc[-1]
            ema_16 = live_data['16_day_MA'].iloc[-1]
            latest_time = live_data.index[-1]

            if ema_8 > ema_16:
             trend_text = "Uptrend"
             trend_color = "green"
            else:
             trend_text = "Downtrend "
             trend_color = "red"

            # Plotting
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(live_data.index, live_data['Close'], label='Close Price', color='orange')
            ax.plot(live_data.index, live_data['8_day_MA'], label='EMA 8', linestyle='--', color='green')
            ax.plot(live_data.index, live_data['16_day_MA'], label='EMA 16', linestyle='--', color='blue')

            for time, price in supports:
                ax.scatter(time, price, color='green', marker='^', s=100)
                ax.axhline(y=price, color='green', linestyle='dashed', alpha=0.2)

            for time, price in resistances:
                ax.scatter(time, price, color='red', marker='v', s=100)
                ax.axhline(y=price, color='red', linestyle='dashed', alpha=0.3)

            # Buy/Sell logic
            resistance_prices = []
            for r in resistances:
              resistance_prices.append(r[1])

            support_prices = []
            for s in supports:
              support_prices.append(s[1])

            if trend_text == "Uptrend" and resistance_prices and latest_price > resistance_prices[-1]:
                ax.scatter(latest_time, latest_price, color='green', marker='o', s=200, label='Long Signal')
                ax.text(latest_time, latest_price, 'Long', fontsize=12, color='green', weight='bold', ha='right')

            if trend_text == "Downtrend" and support_prices and latest_price < support_prices[-1]:
                ax.scatter(latest_time, latest_price, color='red', marker='o', s=200, label='Short Signal')
                ax.text(latest_time, latest_price, 'Short', fontsize=12, color='red', weight='bold', ha='right')

            # Title and labels
            ax.set_title(f'{symbol} - ${latest_price:.2f} | {trend_text}' ,color=trend_color)
            ax.set_xlabel("Time")
            ax.set_ylabel("Price (USD)")
            ax.legend()
            ax.grid(True)
            fig.autofmt_xdate()


            # Convert to base64
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format="png")
            buf.seek(0)
            image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
            plt.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Crypto Chart</title>
    <style>
        body {
            background-color: #131722;
            color: #E0E0E0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-align: center;
            padding: 30px;
        }
        h2 {
            color: #f2f2f2;
        }
        label {
            font-size: 18px;
            margin-right: 10px;
        }
        select {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #1e222d;
            color: #f2f2f2;
            border: 1px solid #333;
            border-radius: 6px;
        }
        button {
            padding: 10px 25px;
            background-color: #2962FF;
            color: white;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            margin-left: 10px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0039cb;
        }
        img {
            margin-top: 30px;
            border: 2px solid #333;
            box-shadow: 0px 0px 20px rgba(0,0,0,0.5);
            max-width: 90%;
        }
        .error {
            color: #ff4d4d;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h2>Select Cryptocurrency</h2>
    <form method="POST">
        <label for="coin">Choose a coin:</label>
        <select name="coin" id="coin">
            <option value="BTC">BTC</option>
            <option value="ETH">ETH</option>
        </select>
        <button type="submit">Show Chart</button>
    </form>

    {% if image_base64 %}
        <h3 style="color:#00e676;">Chart for {{ symbol }}</h3>
        <img src="data:image/png;base64,{{ image_base64 }}" />
    {% endif %}

    {% if error %}
        <p class="error">{{ error }}</p>
    {% endif %}
</body>
</html>
""", image_base64=image_base64, symbol=symbol, error=error)



if __name__ == "__main__":
    app.run(debug=True)
