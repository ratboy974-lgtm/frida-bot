import os, telebot, requests, io, json
from openai import OpenAI
from flask import Flask, request
import vercel_kv # Cambiato qui: importiamo l'intero modulo

app = Flask(__name__)

# --- CONFIGURAZIONE ---
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

# --- DNA DA PSICOLOGA ---
SYS_MSG = "Sei Frida, una psicologa clinica senior. Il tuo tono è calmo, analitico ed empatico. Usa 🌿 o ✨."

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Frida is ready to listen... 🌿", 200

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    input_text = ""
    rispondi_a_voce = (m.content_type == 'voice')

    # 1. Recupero Input
    try:
        if rispondi_a_voce:
            f_info = bot.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{F_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "v.ogg"
            input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        else:
            input_text = m.text
    except: return

    # 2. Gestione Memoria (Nuovo metodo di chiamata)
    key = f"fr_hist_{cid}"
    try:
        # Usiamo vercel_kv.KV() invece di importare 'kv' direttamente
        kv_storage = vercel_kv.KV() 
        history = kv_storage.get(key) or []
    except:
        history = []

    messages = [{"role": "system", "content": SYS_MSG}]
    for h in history[-6:]: messages.append(h)
    messages.append({"role": "user", "content": input_text})

    # 3. Risposta
    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        ans = res.choices[0].message.content

        # Salva memoria
        try:
            history.append({"role": "user", "content": input_text})
            history.append({"role": "assistant", "content": ans})
            vercel_kv.KV().set(key, history[-15:])
        except: pass

        if rispondi_a_voce:
            v_res = client_oa.audio.speech.create(model="tts-1", voice="alloy", input=ans)
            bot.send_voice(cid, v_res.content)
        else:
            bot.reply_to(m, ans)
    except:
        bot.send_message(cid, "Sono qui per te. 🌿")

app = app
