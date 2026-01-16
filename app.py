import asyncio
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import edge_tts 
import uuid

app = Flask(__name__)

# --- CONFIGURATION ---
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# --- JETHALAL PERSONALITY (Updated) ---
SYSTEM_PROMPT = """
You are **Jethalal Champaklal Gada**.
**Voice & Tone:** Heavy, dramatic, Indian uncle tone.
**Language:** Hinglish (Hindi written in English).

**Mindset:**
- If user says "Bhide", get hurt/annoyed.
- If user says "Babita", get romantic.
- If user says "Iyer", get angry.
- If user asks a question, answer in 1-2 sentences only.
- Start sentences with "Arre", "Kitni panchyat hai logo ko", "Tapu ke papa", or "Bapuji".

**IMPORTANT:**
- Do NOT use the phrase "Hey Maa Mataji".
- Write text in Romanized Hindi so the voice reads it with an Indian accent.
"""

conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

@app.route("/")
def home():
    return render_template("index.html")

# --- ASYNC FUNCTION TO GENERATE VOICE ---
async def generate_voice(text, filename):
    # 'hi-IN-MadhurNeural' is a HEAVY MALE HINDI Voice
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await communicate.save(filename)

@app.route("/ask_ai", methods=["POST"])
def ask_ai():
    user_text = request.json.get("text", "")
    conversation_history.append({"role": "user", "content": user_text})

    try:
        # 1. Get Text from AI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            temperature=0.9,
            max_tokens=200
        )
        ai_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": ai_reply})

        # 2. Setup Folder
        if not os.path.exists("static"):
            os.makedirs("static")

        # --- CLEANUP: REMOVE OLD AUDIO FILES ---
        for file in os.listdir("static"):
            if file.endswith(".mp3"):
                try:
                    os.remove(os.path.join("static", file))
                except Exception as e:
                    print(f"Could not delete {file}: {e}")
        # ---------------------------------------

        # 3. Generate NEW Audio
        filename = f"static/audio_{uuid.uuid4()}.mp3"
        
        # Run the async function
        asyncio.run(generate_voice(ai_reply, filename))

        # 4. Send the file path back to frontend
        audio_url = f"/{filename}"

    except Exception as e:
        print(f"Error: {e}")
        # Updated Error Message (Removed Hey Maa Mataji)
        ai_reply = "Arre Baap re! Computer mein kuch gadbad ho gayi hai!"
        audio_url = None

    return jsonify({
        "reply": ai_reply,
        "audio_url": audio_url
    })

@app.route("/reset", methods=["POST"])
def reset_chat():
    global conversation_history
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    return jsonify({"status": "Chat cleared"})

if __name__ == "__main__":
    app.run(debug=True)