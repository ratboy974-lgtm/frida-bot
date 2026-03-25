import os, telebot, requests, io, json
from openai import OpenAI
from flask import Flask, request
from vercel_kv import kv # Ecco la memoria di Frida

app = Flask(__name__)
F_TK = os.environ.get('TOKEN_FRIDA', "").strip()
OA_K = os.environ.get('OPENAI_API_KEY', "").strip()
OR_K = os.environ.get('OPENROUTER_API_KEY', "").strip()

client_oa = OpenAI(api_key=OA_K)
client_or = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OR_K)
bot = telebot.TeleBot(F_TK, threaded=False)

# --- PROMPT PSICOLOGA CLINICA ---
SYS_MSG = (
    "Sei Frida, una psicologa clinica senior. Il tuo compito è l'ascolto profondo. "
    "Analizza i messaggi passati per trovare collegamenti e schemi nel comportamento. "
    "Sii calma, empatica e usa la tecnica del 'Riflesso': riassumi cosa prova il paziente "
    "e fagli domande aperte. Sii sintetica. Usa 🌿 o ✨."
)

@app.route('/', methods=['GET', 'POST'])
def handle_webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return "!", 200
    return "Frida is ready to listen... 🌿", 200

@bot.message_handler(content_types=['text', 'voice'])
def handle_msg(m):
    cid = str(m.chat.id)
    rispondi_a_voce = m.content_type == 'voice'
    
    if rispondi_a_voce:
        f_info = bot.get_file(m.voice.file_id)
        audio = requests.get(f"https://api.telegram.org/file/bot{F_TK}/{f_info.file_path}").content
        audio_io = io.BytesIO(audio); audio_io.name = "v.ogg"
        input_text = client_oa.audio.transcriptions.create(model="whisper-1", file=audio_io).text
    else:
        input_text = m.text

    # --- MEMORIA KV ---
    key = f"frida_history_{cid}"
    history = kv.get(key) or []
    
    messages = [{"role": "system", "content": SYS_MSG}]
    for h in history[-8:]: # Ricorda gli ultimi 8 messaggi
        messages.append(h)
    messages.append({"role": "user", "content": input_text})

    try:
        res = client_or.chat.completions.create(model="google/gemini-2.0-flash-001", messages=messages)
        ans = res.choices[0].message.content

        # Salva in KV
        history.append({"role": "user", "content": input_text})
        history.append({"role": "assistant", "content": ans})
        kv.set(key, history[-30:]) # Salva fino a 30 messaggi

        if rispondi_a_voce:
            v_res = client_oa.audio.speech.create(model="tts-1", voice="alloy", input=ans)
            bot.send_voice(cid, v_res.content)
        else:
            bot.reply_to(m, ans)
    except:
        bot.send_message(cid, "Sono qui per te. Prova a scrivermi di nuovo. 🌿")
