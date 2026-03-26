import os, telebot, requests, io
from openai import OpenAI
from flask import Flask, request

app = Flask(__name__)
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        try:
            # Legge l'invio di Telegram
            json_data = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_data)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Errore: {e}")
        return "OK", 200
    return "Frida is ready to listen... 🌿", 200

@bot.message_handler(func=lambda m: True, content_types=['text', 'voice'])
def handle_msg(m):
    # Risposta immediata per vedere se è vivo
    bot.reply_to(m, "Ti sto ascoltando, dammi un istante... 🌿")
    
    input_text = m.text if m.content_type == 'text' else "Audio ricevuto"
    
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": "Sei Frida, psicologa empatica. Usa 🌿."}, 
                      {"role": "user", "content": input_text}]
        )
        bot.send_message(m.chat.id, res.choices[0].message.content)
    except Exception as e:
        bot.send_message(m.chat.id, "C'è un piccolo intoppo, ma sono qui. ✨")
