     import os
     import datetime
     import yahoo_finance2
     import telegram
     from technicalindicators import EMA, RSI
     from dotenv import load_dotenv

     # Load environment (di Render di-set manual, bukan dari .
     env github)
     load_dotenv()                                              
     TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
     CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
     VIRTUAL_CAPITAL = float(os.getenv('VIRTUAL_CAPITAL',
     1000))
     MAX_TRADES_PER_DAY = int(os.getenv('MAX_TRADES_PER_DAY',
     2))
     DAILY_LOSS_LIMIT = float(os.getenv('DAILY_LOSS_LIMIT',          10))
     SYMBOL = os.getenv('SYMBOL', 'NDX')                             STRATEGY = os.getenv('STRATEGY', 'vwap_ema_rsi')                TIMEZONE = os.getenv('TIMEZONE', 'Asia/Makassar')          
     # Risk management params
     RISK_PERCENT = 1.0  # 1% per trade
     RR_RATIO = 2.0      # 1:2 Risk:Reward

     def calculate_vwap(data):
         """Hitung VWAP dari data OHLCV"""
         typical_price = (data['high'] + data['low'] + data[
     'close']) / 3
         vwap = typical_price.cumsum() / data['volume'].
     cumsum()
         returmessage
def fetch_ndx_data():
         """Ambil data NDX/US100 dari Yahoo Finance (5menit
     interval)"""
         try:
             data = yahoo_finance2.get_history(
                 symbol=SYMBOL,
                 interval="5m",
                 range_size="1d"
             )
             return data
         except Exception as e:
             print(f"Error fetch data: {e}")
             return None

     def calculate_indicators(data):
         """Hitung EMA, RSI, VWAP dari data"""
         if data is None or len(data) < 50:
             return None

         closes = data['close'].values
         highs = data['high'].values
         lows = data['low'].values
         volumes = data['volume'].values

         # EMA 9 dan EMA 21
         ema9 = EMA.calculate({'close': closes, 'period': 9})
         ema21 = EMA.calculate({'close': closes, 'period': 21}
     )

         # RSI 14
         rsi = RSI.calculate({'close': closes, 'period': 14})

         # VWAP
         vwap = calculate_vwap(data)

         return {
             'ema9': ema9,
             'ema21': ema21,
             'rsi': rsi,
             'vwap': vwap,
             'closes': closes,
             'highs': highs,
             'lows': lows
         }
       def check_signals(indicators, current_price, current_index):
         """Cek signal entry berdasarkan strategi VWAP + EMA + RSI"""
         if indicators is None:
             return None

         ema9 = indicators['ema9'][current_index]
         ema21 = indicators['ema21'][current_index]
         rsi = indicators['rsi'][current_index]
         vwap = indicators['vwap'][current_index]

         signals = []

         # --- SETUP 1: Morning Opening Range (09:30-10:30 WIB) ---
         if current_price > vwap and ema9 > ema21 and 30 < rsi < 70:
             signals.append({
                 'side': 'BUY',
                 'entry': current_price,
                 'sl': current_price * (1 - RISK_PERCENT/100),
                 'tp': current_price * (1 + RR_RATIO * RISK_PERCENT/100),
                 'reason': 'Morning VWAP+EMA crossover'
             })

         elif current_price < vwap and ema9 < ema21 and 30 < rsi < 70:
             signals.append({
                 'side': 'SELL',
                 'entry': current_price,
                 'sl': current_price * (1 + RISK_PERCENT/100),
                 'tp': current_price * (1 - RR_RATIO * RISK_PERCENT/100),
                 'reason': 'Morning VWAP+EMA crossover short'
             })

         # --- SETUP 2: Afternoon Reversion (14:00-15:00 WIB) ---
         elif indicators['rsi'][current_index] < 30:
             signals.append({
                 'side': 'BUY',
                 'entry': current_price,
                 'sl': current_price * (1 - RISK_PERCENT/100),
                 'tp': current_price * (1 + RR_RATIO * RISK_PERCENT/100),
                 'reason': 'Afternoon RSI oversold mean reversion'
             })
         elif indicators['rsi'][current_index] > 70:
             signals.append({
                 'side': 'SELL',
                 'entry': current_price,
                 'sl': current_price * (1 + RISK_PERCENT/100),
                 'tp': current_price * (1 - RR_RATIO * RISK_PERCENT/100),
                 'reason': 'Afternoon RSI overbought mean reversion'
             })

         return signals if signals else None

     def format_message(signal, capital):
         """Format message Telegram dengan detail trade"""
         side = signal['side']
         entry = signal['entry']
         sl = signal['sl']
         tp = signal['tp']
         risk_pct = abs(entry - sl) / entry * 100
         reward_pct = abs(tp - entry) / entry * 100

         message = f"""📊 ANALISIS NDX/US100 - {datetime.datetime.now().strftime('%d %B %Y')}

     🕐 Setup: {'Pagi' if 8 <= datetime.datetime.now().hour <= 10 else 'Sore'}

     🟢 {side}
        Entry: {entry:.2f}
        SL: {sl:.2f}  (Risk: {risk_pct:.1f}%)
        TP: {tp:.2f}  (Reward: {reward_pct:.1f}%)
        Risk:Reward: 1:2
        Capital: ${capital:.0f}

     ⚠ Hanya 2 trade maksimal hari ini
     """
         return message
       def send_telegram_message(message):
         """Kirim message ke Telegram"""
         if not TELEGRAM_TOKEN or not CHAT_ID:
             print("Telegram token/chats ID not configured")
             return False

         try:
             bot = telegram.Bot(token=TELEGRAM_TOKEN)
             bot.send_message(chat_id=CHAT_ID, text=message)
             print("✅ Telegram message sent")
             return True
         except Exception as e:
             print(f"❌ Error sending Telegram: {e}")
             return False

     def main():
         """Fungsi utama - cek waktu dan execute trade"""
         now = datetime.datetime.now()
         current_wib = now + datetime.timedelta(hours=7)
         current_time_str = current_wib.strftime('%H:%M:%S')
         current_price_data = fetch_ndx_data()

         print(f"🕐 Current time WIB: {current_time_str}")

         execute = False

         if current_wib.hour == 8 and current_wib.minute < 5:
             execute = True
             session = "morning"
         elif current_wib.hour == 14 and current_wib.minute < 5:
             execute = True
             session = "afternoon"

         if not execute:
             print("⏳ Bukan jadwal trading, cek lagi nanti...")
             return

         if current_price_data is None:
             print("❌ Gagal fetch data NDX")
             return

         indicators = calculate_indicators(current_price_data)
         if indicators is None:
             print("❌ Gagal calculate indicator")
             return

         current_price = current_price_data['close'][-1]
         current_index = len(current_price_data['close']) - 1

         signals = check_signals(indicators, current_price, current_index)

         if signals:
             message = format_message(signals[0], VIRTUAL_CAPITAL)
             send_telegram_message(message)
             print(f"📤 Signal {signals[0]['side']} dikirim ke Telegram")
         else:
             print("⏳ Tidak ada signal trading di sesi ini")

         print(f"📊 Capital: ${VIRTUAL_CAPITAL:.0f} | Risk: {RISK_PERCENT}% per trade")

     if __name__ == "__main__":
         main()
