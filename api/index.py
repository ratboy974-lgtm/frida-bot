import os, telebot, requests, io, json
from openai import OpenAI
from flask import Flask, request

# Proviamo a caricare KV, se fallisce non blocchiamo tutto
try:
    from vercel_kv import kv
    KV_AVAILABLE = True
except ImportError:
    KV_AVAILABLE = False

app = Flask(__name__)

# --- CONFIGURAZIONE ---
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

SYS_MSG = "Sei Frida, una psicologa empatica e profonda. Usa 🌿 o ✨."

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Errore Webhook: {e}")
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
    except:
        return

    # 2. Memoria (Protetta da crash)
    history = []
    if KV_AVAILABLE:
        try:
            history = kv.get(f"fr_hist_{cid}") or []
        except:
            pass

    messages = [{"role": "system", "content": SYS_MSG}]
    for h in history[-6:]: messages.append(h)
    messages.append({"role": "user", "content": input_text})

    # 3. Risposta
    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        ans = res.choices[0].message.content

        # Salva se possibile
        if KV_AVAILABLE:
            try:
                history.append({"role": "user", "content": input_text})
                history.append({"role": "assistant", "content": ans})
                kv.set(f"fr_hist_{cid}", history[-15:])
            except: pass

        if rispondi_a_voce:
            v_res = client_oa.audio.speech.create(model="tts-1", voice="alloy", input=ans)
            bot.send_voice(cid, v_res.content)
        else:
            bot.reply_to(m, ans)
    except:
        bot.send_message(cid, "Sono qui per te. 🌿")

app = app
