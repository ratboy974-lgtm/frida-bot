import os, telebot, requests, io
from openai import OpenAI
from flask import Flask, request

app = Flask(__name__)

# --- CONFIGURAZIONE ---
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

SYS_MSG = "Sei Frida, psicologa empatica. Parla con calma e usa 🌿."

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return "!", 200
    return "Frida is ready to listen... 🌿", 200

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = m.chat.id
    input_text = m.text if m.content_type == 'text' else "Audio ricevuto"
    
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[{"role": "system", "content": SYS_MSG}, {"role": "user", "content": input_text}]
        )
        bot.reply_to(m, res.choices[0].message.content)
    except:
        bot.send_message(cid, "Sono qui. Riprova. 🌿")
