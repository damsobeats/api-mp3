import os
import glob

from flask import Flask, request, send_file, jsonify
import yt_dlp

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def safe_filename(text):
    forbidden = '<>:"/\\|?*'
    text = "".join("_" if c in forbidden else c for c in text)
    text = text.strip()

    if not text:
        text = "audio"

    return text[:180]


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "yt_dlp": yt_dlp.version.__version__
    })


@app.route("/download", methods=["GET"])
def download_audio():

    artiste = request.args.get("artiste", "").strip()
    titre = request.args.get("titre", "").strip()

    if not artiste or not titre:
        return jsonify({
            "erreur": "Veuillez fournir artiste et titre."
        }), 400

    if not os.path.exists(COOKIES_FILE):
        return jsonify({
            "erreur": "cookies.txt introuvable"
        }), 500

    nom = safe_filename(f"{artiste} - {titre}")
    output_template = os.path.join(
        DOWNLOAD_DIR,
        nom + ".%(ext)s"
    )

    requete = f"ytsearch1:{artiste} - {titre}"

    options = {
        "format": "ba/b",

        "cookiefile": COOKIES_FILE,

        "extractor_args": {
            "youtube": {
                "player_client": [
                    "default",
                    "web_safari"
                ]
            }
        },

        "noplaylist": True,

        "outtmpl": output_template,

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }
        ],

        "quiet": False,
        "no_warnings": False,

        "retries": 3,
        "fragment_retries": 3,

        "nocheckcertificate": True
    }

    try:

        print("=" * 60)
        print("NOUVEAU TELECHARGEMENT")
        print("=" * 60)

        print("Artiste :", artiste)
        print("Titre :", titre)
        print("Recherche :", requete)
        print("yt-dlp :", yt_dlp.version.__version__)
        print("Cookies :", COOKIES_FILE)

        with yt_dlp.YoutubeDL(options) as ydl:

            print("Recherche YouTube...")

            info = ydl.extract_info(
                requete,
                download=False
            )

            if not info:
                return jsonify({
                    "erreur": "Aucun résultat trouvé"
                }), 404

            if "entries" in info:

                entries = [
                    entry for entry in info["entries"]
                    if entry
                ]

                if not entries:
                    return jsonify({
                        "erreur": "Aucune vidéo trouvée"
                    }), 404

                info = entries[0]

            video_id = info.get("id")
            video_title = info.get("title")

            print("Video ID :", video_id)
            print("Titre YouTube :", video_title)

            formats = info.get("formats", [])

            print("=" * 60)
            print("FORMATS DISPONIBLES :", len(formats))
            print("=" * 60)

            for f in formats:

                print(
                    "id=", f.get("format_id"),
                    "| ext=", f.get("ext"),
                    "| audio=", f.get("acodec"),
                    "| video=", f.get("vcodec"),
                    "| abr=", f.get("abr"),
                    "| protocole=", f.get("protocol")
                )

            audio_formats = [
                f for f in formats
                if f.get("acodec")
                and f.get("acodec") != "none"
            ]

            if not audio_formats:

                return jsonify({
                    "erreur": "Aucun format audio fourni par YouTube",
                    "video_id": video_id,
                    "video_title": video_title,
                    "nombre_formats": len(formats),
                    "yt_dlp": yt_dlp.version.__version__
                }), 502

            print("=" * 60)
            print("TELECHARGEMENT...")
            print("=" * 60)

            ydl.download([requete])

        expected_file = os.path.join(
            DOWNLOAD_DIR,
            nom + ".mp3"
        )

        if os.path.exists(expected_file):

            print("MP3 créé :", expected_file)

            return send_file(
                expected_file,
                as_attachment=True,
                download_name=nom + ".mp3",
                mimetype="audio/mpeg"
            )

        mp3_files = glob.glob(
            os.path.join(DOWNLOAD_DIR, "*.mp3")
        )

        if mp3_files:

            mp3_files.sort(
                key=os.path.getmtime,
                reverse=True
            )

            latest = mp3_files[0]

            print("MP3 trouvé :", latest)

            return send_file(
                latest,
                as_attachment=True,
                download_name=nom + ".mp3",
                mimetype="audio/mpeg"
            )

        return jsonify({
            "erreur": "yt-dlp a terminé mais aucun MP3 n'a été trouvé"
        }), 500

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({
            "erreur": str(e),
            "type": type(e).__name__
        }), 500


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
