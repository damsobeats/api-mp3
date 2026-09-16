import os
import shutil
import tempfile
from flask import Flask, after_this_request, jsonify, request, send_file
import yt_dlp

app = Flask(__name__)


@app.route("/download", methods=["GET"])
def download_audio():
    artiste = request.args.get("artiste")
    titre = request.args.get("titre")

    if not artiste or not titre:
        return (
            jsonify({"erreur": "Veuillez fournir un artiste et un titre."}),
            400,
        )

    # Dossier de travail temporaire isolé
    temp_dir = tempfile.mkdtemp()

    @after_this_request
    def cleanup(response):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return response

    safe_title = f"{artiste} - {titre}".replace("/", "_").replace("\\", "_")
    output_tmpl = os.path.join(temp_dir, "%(title)s.%(ext)s")
    requete = f"ytsearch1:{artiste} - {titre} audio"

    options = {
        "format": "bestaudio/best",
        "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None,
        "extractor_args": {
            "youtube": {
                "player_client": ["android_music", "android", "ios"],
                "player_skip": ["webpage", "configs"],
            }
        },
        "http_headers": {
            "User-Agent": (
                "com.google.android.apps.youtube.music/6.20.51 (Linux; U;"
                " Android 14; fr_FR; Pixel 7 Pro) gzip"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_tmpl,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([requete])

        # Recherche automatique du fichier audio généré dans le dossier temporaire
        generated_files = [
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if os.path.isfile(os.path.join(temp_dir, f))
            and not f.endswith(".part")
            and not f.endswith(".ytdl")
        ]

        if not generated_files:
            return (
                jsonify({
                    "erreur": "Aucun fichier n'a été produit par le téléchargement."
                }),
                500,
            )

        # Sélection prioritaire du fichier MP3 généré par FFmpeg
        mp3_files = [f for f in generated_files if f.lower().endswith(".mp3")]
        target_file = mp3_files[0] if mp3_files else generated_files[0]

        return send_file(
            target_file,
            as_attachment=True,
            download_name=f"{safe_title}.mp3",
            mimetype="audio/mpeg",
        )

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "message": "API YouTube MP3 active"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
