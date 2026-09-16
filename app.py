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

    temp_dir = tempfile.mkdtemp()

    @after_this_request
    def cleanup(response):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return response

    safe_title = f"{artiste} - {titre}".replace("/", "_").replace("\\", "_")
    target_output = os.path.join(temp_dir, "output.%(ext)s")
    final_mp3 = os.path.join(temp_dir, "output.mp3")

    # Options pour la recherche et extraction
    ydl_opts = {
        "format": "bestaudio/best",
        "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "player_skip": ["webpage", "configs"],
            }
        },
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": target_output,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }

    try:
        query = f"ytsearch1:{artiste} {titre} audio"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Recherche explicite de la vidéo
            search_results = ydl.extract_info(query, download=False)
            if not search_results or "entries" not in search_results or not search_results["entries"]:
                return jsonify({"erreur": "Aucune vidéo trouvée sur YouTube."}), 404

            video_info = search_results["entries"][0]
            video_url = video_info.get("webpage_url") or video_info.get("url")

            # Téléchargement direct de l'URL résolue
            ydl.download([video_url])

        # Vérification du fichier MP3 généré
        if os.path.exists(final_mp3) and os.path.getsize(final_mp3) > 1000:
            return send_file(
                final_mp3,
                as_attachment=True,
                download_name=f"{safe_title}.mp3",
                mimetype="audio/mpeg",
            )

        # Fallback de détection si FFmpeg a conservé une autre extension
        generated_files = [
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if os.path.isfile(os.path.join(temp_dir, f))
            and not f.endswith((".part", ".ytdl"))
        ]

        if generated_files:
            return send_file(
                generated_files[0],
                as_attachment=True,
                download_name=f"{safe_title}.mp3",
                mimetype="audio/mpeg",
            )

        return (
            jsonify({"erreur": "Le fichier audio n'a pas pu être extrait."}),
            500,
        )

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "message": "API YouTube MP3 active"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
