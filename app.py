import os
import shutil
import tempfile
from flask import Flask, after_this_request, jsonify, request, send_file
import yt_dlp

app = Flask(__name__)


@app.route('/download', methods=['GET'])
def download_audio():
  artiste = request.args.get('artiste')
  titre = request.args.get('titre')

  if not artiste or not titre:
    return (
        jsonify({'erreur': 'Veuillez fournir un artiste et un titre.'}),
        400,
    )

  # Dossier temporaire isolé pour chaque téléchargement
  temp_dir = tempfile.mkdtemp()

  @after_this_request
  def cleanup(response):
    # Nettoyage automatique du dossier temporaire après l'envoi de la réponse
    shutil.rmtree(temp_dir, ignore_errors=True)
    return response

  safe_title = f'{artiste} - {titre}'.replace('/', '_').replace('\\', '_')
  output_base = os.path.join(temp_dir, 'audio')
  final_mp3 = f'{output_base}.mp3'
  requete = f'ytsearch1:{artiste} - {titre} audio'

  options = {
      'format': 'bestaudio/best',
      'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
      # Force les clients mobiles pour contourner la détection de bot sur IP datacenter
      'extractor_args': {
          'youtube': {
              'player_client': ['android_music', 'android', 'ios'],
              'player_skip': ['webpage', 'configs'],
          }
      },
      'http_headers': {
          'User-Agent': (
              'com.google.android.apps.youtube.music/6.20.51 (Linux; U; Android'
              ' 14; fr_FR; Pixel 7 Pro) gzip'
          ),
          'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
      },
      'postprocessors': [{
          'key': 'FFmpegExtractAudio',
          'preferredcodec': 'mp3',
          'preferredquality': '192',
      }],
      'outtmpl': f'{output_base}.%(ext)s',
      'noplaylist': True,
      'quiet': False,
      'no_warnings': False,
      'nocheckcertificate': True,
  }

  try:
    with yt_dlp.YoutubeDL(options) as ydl:
      ydl.download([requete])

    if os.path.exists(final_mp3) and os.path.getsize(final_mp3) > 1000:
      return send_file(
          final_mp3,
          as_attachment=True,
          download_name=f'{safe_title}.mp3',
          mimetype='audio/mpeg',
      )
    else:
      return (
          jsonify({
              'erreur': 'Le fichier MP3 n\'a pas pu être généré par FFmpeg.'
          }),
          500,
      )

  except Exception as e:
    return jsonify({'erreur': str(e)}), 500


@app.route('/', methods=['GET'])
def health():
  return jsonify({'status': 'online', 'message': 'API YouTube MP3 active'})


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
