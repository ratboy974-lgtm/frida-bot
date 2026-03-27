import os, telebot, requests, io, json
from openai import OpenAI
from flask import Flask, request

# Importazione super-sicura di vercel_kv
try:
    import vercel_kv
    HAS_KV = True
except:
    HAS_KV = False

app = Flask(__name__)

# --- CONFIGURAZIONE ---
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

SYS_MSG = "Sei Frida, una psicologa clinica senior. Il tuo tono è calmo, analitico ed empatico. Usa 🌿 o ✨."

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Errore Update: {e}")
        return "OK", 200
    return "Frida is ready to listen... 🌿", 200

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    input_text = ""
    
    # 1. Recupero Testo/Audio
    try:
        if m.content_type == 'voice':
            f_info = bot.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{F_TK}/{f_info.file_path}").content
            audio_io = io.BytesIO(audio); audio_io.name = "v.ogg"
            input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
        else:
            input_text = m.text
    except: return

    # 2. Recupero Memoria (Senza crash)
    history = []
    if HAS_KV:
        try:
            # Nuovo metodo di connessione raccomandato
            kv = vercel_kv.KV()
            history = kv.get(f"hist_{cid}") or []
        except: pass

    messages = [{"role": "system", "content": SYS_MSG}]
    for h in history[-6:]: messages.append(h)
    messages.append({"role": "user", "content": input_text})

    # 3. Risposta IA
    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        ans = res.choices[0].message.content

        # 4. Salvataggio Memoria
        if HAS_KV:
            try:
                history.append({"role": "user", "content": input_text})
                history.append({"role": "assistant", "content": ans})
                vercel_kv.KV().set(f"hist_{cid}", history[-15:])
            except: pass

        # 5. Invio Risposta
        if m.content_type == 'voice':
            v_res = client_oa.audio.speech.create(model="tts-1", voice="alloy", input=ans)
            bot.send_voice(cid, v_res.content)
        else:
            bot.reply_to(m, ans)
    except:
        bot.send_message(cid, "Sono qui, ti ascolto. 🌿")

app = app
