import os
from flask import Flask, request, send_file, jsonify
import yt_dlp

app = Flask(__name__)

@app.route('/download', methods=['GET'])
def download_audio():
    artiste = request.args.get('artiste')
    titre = request.args.get('titre')
    
    if not artiste or not titre:
        return jsonify({"erreur": "Veuillez fournir un artiste et un titre."}), 400

    requete = f"ytsearch1:{artiste} - {titre}"
    filename = f"{artiste} - {titre}.mp3".replace("/", "_")
    
    options = {
        'format': 'bestaudio/best',
        'cookiefile': 'cookies.txt',  # <-- Ligne à ajouter ici
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': filename.replace('.mp3', ''),
    }
        'outtmpl': filename.replace('.mp3', ''),
    } 

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([requete])
            
        if os.path.exists(filename):
            return send_file(filename, as_attachment=True)
        else:
            return jsonify({"erreur": "Le fichier n'a pas pu être généré."}), 500

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
