```python
import os
import glob
import shutil
import tempfile
from urllib.parse import quote

from flask import Flask, request, send_file, jsonify
import yt_dlp


app = Flask(__name__)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

# Dossier temporaire pour les téléchargements
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ---------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------

def safe_filename(text):
    """
    Nettoie un nom de fichier pour Linux.
    """
    forbidden = '<>:"/\\|?*'
    text = "".join("_" if c in forbidden else c for c in text)

    # Évite les noms trop longs
    text = text.strip()

    if not text:
        text = "audio"

    return text[:180]


def cleanup_file(path):
    """
    Supprime un fichier s'il existe.
    """
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ---------------------------------------------------------
# Route principale
# ---------------------------------------------------------

@app.route("/download", methods=["GET"])
def download_audio():

    artiste = request.args.get("artiste", "").strip()
    titre = request.args.get("titre", "").strip()

    if not artiste or not titre:
        return jsonify({
            "erreur": "Veuillez fournir artiste et titre."
        }), 400

    # -----------------------------------------------------
    # Recherche YouTube
    # -----------------------------------------------------

    requete = f"ytsearch1:{artiste} - {titre}"

    filename = safe_filename(
        f"{artiste} - {titre}"
    ) + ".mp3"

    output_template = os.path.join(
        DOWNLOAD_DIR,
        safe_filename(f"{artiste} - {titre}") + ".%(ext)s"
    )

    # -----------------------------------------------------
    # Vérification cookies
    # -----------------------------------------------------

    if not os.path.exists(COOKIES_FILE):
        return jsonify({
            "erreur": "cookies.txt introuvable.",
            "chemin": COOKIES_FILE
        }), 500

    # -----------------------------------------------------
    # Options yt-dlp
    # -----------------------------------------------------

    ydl_opts = {

        # Audio uniquement.
        #
        # ba = meilleur flux audio seul
        # b  = meilleur format combiné disponible
        #
        # Le "/" fournit un fallback.
        "format": "ba/b",

        # Cookies YouTube
        "cookiefile": COOKIES_FILE,

        # Clients YouTube.
        #
        # web_safari est intéressant actuellement car yt-dlp
        # indique qu'il peut fournir des formats HLS.
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "default",
                    "web_safari"
                ]
            }
        },

        # Pas de playlist
        "noplaylist": True,

        # Sortie
        "outtmpl": output_template,

        # FFmpeg
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],

        # Logs.
        #
        # IMPORTANT :
        # mettre False pendant le diagnostic Render.
        "quiet": False,
        "no_warnings": False,

        # Réseau
        "nocheckcertificate": True,

        # Quelques tentatives supplémentaires
        "retries": 3,
        "fragment_retries": 3,

        # Évite certains problèmes avec les playlists
        "ignoreerrors": False,

        # Ne télécharge pas les métadonnées inutiles
        "writethumbnail": False,
        "writeinfojson": False,
        "writesubtitles": False,
    }

    # -----------------------------------------------------
    # Téléchargement
    # -----------------------------------------------------

    try:

        print("=" * 70)
        print("NOUVEAU TELECHARGEMENT")
        print("=" * 70)

        print("Artiste :", artiste)
        print("Titre   :", titre)
        print("Recherche :", requete)

        print("yt-dlp :", yt_dlp.version.__version__)
        print("Cookies :", COOKIES_FILE)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            # -------------------------------------------------
            # Première étape :
            # récupérer les informations sans télécharger
            # -------------------------------------------------

            print("Extraction des informations YouTube...")

            info = ydl.extract_info(
                requete,
                download=False
            )

            if not info:
                return jsonify({
                    "erreur": "Aucun résultat YouTube."
                }), 404

            # Si la recherche retourne une playlist de résultats,
            # on prend le premier.
            if "entries" in info:
                entries = [
                    entry
                    for entry in info["entries"]
                    if entry
                ]

                if not entries:
                    return jsonify({
                        "erreur": "Aucune vidéo trouvée."
                    }), 404

                info = entries[0]

            video_id = info.get("id")
            video_title = info.get("title")

            print("Video ID :", video_id)
            print("Titre YouTube :", video_title)

            # -------------------------------------------------
            # Affichage des formats disponibles
            # -------------------------------------------------

            formats = info.get("formats", [])

            print("-" * 70)
            print("FORMATS DISPONIBLES :", len(formats))
            print("-" * 70)

            for f in formats:

                print(
                    "id=",
                    f.get("format_id"),
                    "| ext=",
                    f.get("ext"),
                    "| acodec=",
                    f.get("acodec"),
                    "| vcodec=",
                    f.get("vcodec"),
                    "| abr=",
                    f.get("abr"),
                    "| protocol=",
                    f.get("protocol"),
                )

            print("-" * 70)

            # -------------------------------------------------
            # Vérification qu'un format audio existe
            # -------------------------------------------------

            audio_formats = [
                f for f in formats
                if f.get("acodec")
                and f.get("acodec") != "none"
            ]

            if not audio_formats:

                return jsonify({
                    "erreur": "YouTube n'a fourni aucun format audio exploitable.",
                    "video_id": video_id,
                    "video_title": video_title,
                    "yt_dlp_version": yt_dlp.version.__version__,
                    "formats_count": len(formats),
                }), 502

            # -------------------------------------------------
            # Téléchargement réel
            # -------------------------------------------------

            print("Téléchargement...")

            ydl.download([requete])

        # -----------------------------------------------------
        # Recherche du MP3 produit
        # -----------------------------------------------------

        expected_file = os.path.join(
            DOWNLOAD_DIR,
            filename
        )

        print("Fichier attendu :", expected_file)

        if os.path.exists(expected_file):

            print("MP3 trouvé :", expected_file)

            return send_file(
                expected_file,
                as_attachment=True,
                download_name=filename,
                mimetype="audio/mpeg"
            )

        # -----------------------------------------------------
        # Fallback :
        # chercher le dernier MP3 créé
        # -----------------------------------------------------

        mp3_files = glob.glob(
            os.path.join(DOWNLOAD_DIR, "*.mp3")
        )

        if mp3_files:

            mp3_files.sort(
                key=os.path.getmtime,
                reverse=True
            )

            latest_file = mp3_files[0]

            print("MP3 trouvé via fallback :", latest_file)

            return send_file(
                latest_file,
                as_attachment=True,
                download_name=filename,
                mimetype="audio/mpeg"
            )

        # -----------------------------------------------------
        # Aucun fichier
        # -----------------------------------------------------

        return jsonify({
            "erreur": "yt-dlp n'a pas généré de fichier MP3.",
            "video_id": video_id,
            "video_title": video_title
        }), 500

    except Exception as e:

        print("=" * 70)
        print("ERREUR")
        print("=" * 70)

        import traceback
        traceback.print_exc()

        return jsonify({
            "erreur": str(e),
            "type": type(e).__name__
        }), 500


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "service": "youtube-audio-api",
        "yt_dlp": yt_dlp.version.__version__
    })


# ---------------------------------------------------------
# Lancement local
# ---------------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
```
