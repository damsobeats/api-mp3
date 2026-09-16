import os
import shutil
import tempfile
import urllib.parse
import urllib.request
import json
from flask import Flask, request, send_file, jsonify, after_this_request

app = Flask(__name__)

# Instances fiables pour interroger YouTube sans blocage d'IP
INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
    "https://invidious.protokolla.fi",
    "https://yt.artemislena.eu"
]

def get_audio_stream_url(query):
    encoded_query = urllib.parse.quote(query)
    
    for base_url in INVIDIOUS_INSTANCES:
        try:
            # 1. Recherche du morceau
            search_api = f"{base_url}/api/v1/search?q={encoded_query}&type=video"
            req = urllib.request.Request(search_api, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as response:
                results = json.loads(response.read().decode())
            
            if not results:
                continue
                
            video_id = results[0]["videoId"]
            
            # 2. Récupération des flux audio de la vidéo
            video_api = f"{base_url}/api/v1/videos/{video_id}"
            req_video = urllib.request.Request(video_api, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_video, timeout=6) as response:
                video_data = json.loads(response.read().decode())
                
            audio_formats = video_data.get("adaptiveFormats", [])
            # Filtrer pour ne garder que les flux audio
            audio_streams = [f for f in audio_formats if f.get("type", "").startswith("audio/")]
            
            if audio_streams:
                # Trie par bitrate pour avoir la meilleure qualité
                audio_streams.sort(key=lambda x: int(x.get("bitrate", 0)), reverse=True)
                return audio_streams[0]["url"]
                
        except Exception:
            continue
            
    return None

@app.route("/download", methods=["GET"])
def download_audio():
    artiste = request.args.get("artiste")
    titre = request.args.get("titre")

    if not artiste or not titre:
        return jsonify({"erreur": "Veuillez fournir un artiste et un titre."}), 400

    temp_dir = tempfile.mkdtemp()

    @after_this_request
    def cleanup(response):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return response

    query = f"{artiste} {titre} audio"
    stream_url = get_audio_stream_url(query)

    if not stream_url:
        return jsonify({"erreur": "Impossible d'extraire le flux YouTube actuellement."}), 502

    safe_title = f"{artiste} - {titre}".replace("/", "_").replace("\\", "_")
    raw_file = os.path.join(temp_dir, "input_stream")
    final_mp3 = os.path.join(temp_dir, "output.mp3")

    try:
        # Téléchargement direct du flux audio relayé
        req = urllib.request.Request(stream_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as resp, open(raw_file, "wb") as f:
            f.write(resp.read())

        # Conversion directe en MP3 propre via FFmpeg
        res = os.system(f"ffmpeg -y -i {raw_file} -vn -ar 44100 -ac 2 -b:a 192k {final_mp3} -loglevel quiet")
        
        if res != 0 or not os.path.exists(final_mp3):
            return jsonify({"erreur": "Erreur lors de l'encodage MP3 avec FFmpeg."}), 500

        return send_file(
            final_mp3,
            as_attachment=True,
            download_name=f"{safe_title}.mp3",
            mimetype="audio/mpeg"
        )

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "message": "API YouTube MP3 active"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
