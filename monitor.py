
import requests
import time
import threading
from datetime import datetime

TELEGRAM_BOT_TOKEN = '8183156039:AAEm2qKnA5bGQivpEgXa5wjLCd5a6CMZuTw'
TELEGRAM_CHAT_ID = '-1002813651741'
WAX_ACCOUNT = 'bitgetxpr'
TELOS_ACCOUNT = 'bdhivesteem'
CHECK_INTERVAL = 10

last_wax_tx = None
last_tlos_tx = None
last_update_id = None

def send_telegram_message(msg):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                  data={'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'})

def get_price(symbol):
    try:
        if symbol == 'WAXP':
            url = 'https://api.bybit.com/v2/public/tickers'
            resp = requests.get(url, params={'symbol': 'WAXPUSDT'})
            resp.raise_for_status()
            return float(resp.json()['result'][0]['last_price'])
        elif symbol == 'TLOS':
            url = 'https://api.kucoin.com/api/v1/market/orderbook/level1'
            resp = requests.get(url, params={'symbol': 'TLOS-USDT'})
            resp.raise_for_status()
            return float(resp.json()['data']['price'])
    except Exception as e:
        print(f"Ошибка получения курса {symbol}:", e)
        return 0.0

def get_account_actions(endpoint, account):
    resp = requests.get(f"{endpoint}/v2/history/get_actions", params={'account': account, 'limit': 1})
    resp.raise_for_status()
    return resp.json().get('actions', [])

def monitor():
    global last_wax_tx, last_tlos_tx
    print("▶️ Мониторинг запущен...")
    while True:
        try:
            wax_act = get_account_actions("https://wax.greymass.com", WAX_ACCOUNT)
            if wax_act:
                act = wax_act[0]['act']
                tx_id = wax_act[0]['trx_id']
                bt = wax_act[0]['@timestamp']
                if act['name'] == 'transfer' and act['data']['to'] == WAX_ACCOUNT:
                    if tx_id != last_wax_tx:
                        last_wax_tx = tx_id
                        from_acc = act['data']['from']
                        qty = act['data']['quantity']
                        memo = act['data']['memo']
                        t = datetime.strptime(bt, "%Y-%m-%dT%H:%M:%S.%f")
                        t_str = t.strftime("%Y-%m-%d %H:%M:%S UTC")
                        amount = float(qty.split()[0])
                        price = get_price('WAXP')
                        usd = amount * price
                        txt = (f"📥 *Новый депозит (WAXP)*
"
                               f"👤 Отправитель: `{from_acc}`
"
                               f"💰 Сумма: `{qty}` (~${usd:.4f})
"
                               f"📝 Memo: `{memo}`
"
                               f"🕒 Время: {t_str}")
                        print(txt)
                        send_telegram_message(txt)

            tlos_act = get_account_actions("https://telos.greymass.com", TELOS_ACCOUNT)
            if tlos_act:
                act = tlos_act[0]['act']
                tx_id = tlos_act[0]['trx_id']
                bt = tlos_act[0]['@timestamp']
                if act['name'] == 'transfer' and act['data']['to'] == TELOS_ACCOUNT:
                    if tx_id != last_tlos_tx:
                        last_tlos_tx = tx_id
                        from_acc = act['data']['from']
                        qty = act['data']['quantity']
                        memo = act['data']['memo']
                        t = datetime.strptime(bt, "%Y-%m-%dT%H:%M:%S.%f")
                        t_str = t.strftime("%Y-%m-%d %H:%M:%S UTC")
                        amount = float(qty.split()[0])
                        price = get_price('TLOS')
                        usd = amount * price
                        txt = (f"📥 *Новый депозит (TLOS)*
"
                               f"👤 Отправитель: `{from_acc}`
"
                               f"💰 Сумма: `{qty}` (~${usd:.4f})
"
                               f"📝 Memo: `{memo}`
"
                               f"🕒 Время: {t_str}")
                        print(txt)
                        send_telegram_message(txt)

        except Exception as e:
            print("Ошибка monitor():", e)
        time.sleep(CHECK_INTERVAL)

def listen_commands():
    global last_update_id
    while True:
        try:
            resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                                params={'timeout': 10, 'offset': last_update_id + 1 if last_update_id else None}, timeout=15)
            resp.raise_for_status()
            for upd in resp.json().get('result', []):
                last_update_id = upd['update_id']
                msg = upd.get('message', {})
                if msg.get('text') == '/start' and str(msg.get('chat', {}).get('id')) == TELEGRAM_CHAT_ID:
                    wax_bal = requests.post("https://wax.greymass.com/v1/chain/get_currency_balance",
                        json={"code": "eosio.token", "account": WAX_ACCOUNT, "symbol": "WAX"}).json()
                    tlos_bal = requests.post("https://telos.greymass.com/v1/chain/get_currency_balance",
                        json={"code": "eosio.token", "account": TELOS_ACCOUNT, "symbol": "TLOS"}).json()
                    wb = wax_bal[0] if wax_bal else "0"
                    tb = tlos_bal[0] if tlos_bal else "0"
                    send_telegram_message(f"📊 *Баланс:*
*WAXP:* `{wb}`
*TLOS:* `{tb}`")
        except Exception as e:
            print("Ошибка commands():", e)
        time.sleep(2)

threading.Thread(target=monitor, daemon=True).start()
threading.Thread(target=listen_commands, daemon=True).start()

while True:
    time.sleep(60)
