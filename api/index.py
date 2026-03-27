import os, telebot, requests, io, json
from openai import OpenAI
from flask import Flask, request

# Importazione blindata
try:
    import vercel_kv
    HAS_KV = True
except:
    HAS_KV = False

app = Flask(__name__)

# --- CONFIGURAZIONE (Dalle tue variabili in image_da05b6) ---
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

SYS_MSG = "Sei Frida, una psicologa clinica. Parla in modo calmo ed empatico. Usa 🌿."

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        try:
            bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
        except: pass
        return "!", 200
    return "Frida Online 🌿", 200

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    
    # --- 1. TEST DI RISPOSTA IMMEDIATA ---
    # bot.send_chat_action(cid, 'typing') 

    # --- 2. RECUPERO TESTO ---
    input_text = ""
    try:
        if m.content_type == 'voice':
            f_info = bot.get_file(m.voice.file_id)
            audio = requests.get(f"https://api.telegram.org/file/bot{F_TK}/{f_info.file_path}").content
            transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=("v.ogg", io.BytesIO(audio)))
            input_text = transcript.text
        else:
            input_text = m.text
    except: return

    # --- 3. MEMORIA (Usando l'istanza corretta) ---
    history = []
    if HAS_KV:
        try:
            # Chiamata diretta per evitare l'ImportError dei log
            storage = vercel_kv.KV()
            history = storage.get(f"h_{cid}") or []
        except: pass

    messages = [{"role": "system", "content": SYS_MSG}]
    for h in history[-6:]: messages.append(h)
    messages.append({"role": "user", "content": input_text})

    # --- 4. RISPOSTA IA ---
    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        ans = res.choices[0].message.content

        # Salva memoria
        if HAS_KV:
            try:
                history.append({"role": "user", "content": input_text})
                history.append({"role": "assistant", "content": ans})
                vercel_kv.KV().set(f"h_{cid}", history[-10:])
            except: pass

        # --- 5. INVIO ---
        if m.content_type == 'voice':
            v = client_oa.audio.speech.create(model="tts-1", voice="alloy", input=ans)
            bot.send_voice(cid, v.content)
        else:
            bot.reply_to(m, ans)
    except Exception as e:
        bot.send_message(cid, "Sono qui, ti ascolto. 🌿")
