import os, telebot, requests, io, json
from openai import OpenAI
from flask import Flask, request
from vercel_kv import kv 

app = Flask(__name__)

# --- CONFIGURAZIONE ---
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

# --- DNA DA PSICOLOGA ---
SYS_MSG = (
    "Sei Frida, una psicologa clinica senior. Il tuo tono è calmo, analitico ed empatico. "
    "Usa la memoria dei messaggi passati per identificare schemi ricorrenti. "
    "Sii sintetica ma profonda. Usa 🌿 o ✨."
)

# --- GESTIONE ROTTE (WEBHOOK) ---
@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        # Telegram invia i dati qui
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        # Se apri il link nel browser vedi questo
        return "Frida is ready to listen... 🌿", 200

# --- LOGICA MESSAGGI ---
@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    input_text = ""
    rispondi_a_voce = (m.content_type == 'voice')

    # 1. Recupero Input (Testo o Vocale)
    try:
        if rispondi_a_voce:
            f_info = bot.get_file(m.voice.file_id)
            audio_url = f"https://api.telegram.org/file/bot{F_TK}/{f_info.file_path}"
            audio_content = requests.get(audio_url).content
            audio_io = io.BytesIO(audio_content)
            audio_io.name = "voice.ogg"
            transcript = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io)
            input_text = transcript.text
        else:
            input_text = m.text
    except Exception as e:
        bot.send_message(cid, "Non sono riuscita a sentirti bene... ✨")
        return

    # 2. Gestione Memoria KV
    key = f"frida_hist_{cid}"
    try:
        history = kv.get(key) or []
    except:
        history = []

    # Costruiamo il contesto per l'IA
    messages = [{"role": "system", "content": SYS_MSG}]
    for h in history[-6:]: # Ricorda gli ultimi 6 scambi
        messages.append(h)
    messages.append({"role": "user", "content": input_text})

    # 3. Generazione Risposta
    try:
        res = client_or.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=messages
        )
        ans = res.choices[0].message.content

        # 4. Salvataggio in Memoria
        history.append({"role": "user", "content": input_text})
        history.append({"role": "assistant", "content": ans})
        try:
            kv.set(key, history[-20:]) # Teniamo gli ultimi 20 messaggi
        except:
            pass

        # 5. Invio Risposta (Testo o Vocale)
        if rispondi_a_voce:
            # Voce 'Alloy' (seria ed empatica)
            v_res = client_oa.audio.speech.create(model="tts-1", voice="alloy", input=ans)
            bot.send_voice(cid, v_res.content)
        else:
            bot.reply_to(m, ans)

    except Exception as e:
        bot.send_message(cid, "Prendiamoci un momento di silenzio... riprova tra poco. 🌿")

# Fondamentale per Vercel
app = app
