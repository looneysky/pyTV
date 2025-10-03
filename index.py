import os
import requests
from flask import Flask, request, Response, send_from_directory

app = Flask(__name__)

BASE_URL = 'https://cdntv.online/hls/9mlxywika2'

#powered by dezamorfin

@app.route('/tv/<id>.m3u8')
def relay_playlist(id):
    url = f'{BASE_URL}/{id}.m3u8'
    r = requests.get(url)

    if r.status_code == 200:
        content = r.text
        modified_content = content.replace(BASE_URL, f'http://{os.environ.get("INSTANCE_HOST")}:{os.environ.get("PORT")}/segments/{id}')
        return Response(modified_content, content_type='application/vnd.apple.mpegurl')
    else:
        return Response(f"Error {r.status_code}: Unable to fetch the playlist.", status=r.status_code)

@app.route('/segments/<id>/<path:segment>')
def relay_segment(id, segment):
    url = f'{BASE_URL}/{id}/{segment}'
    r = requests.get(url, stream=True)

    if r.status_code == 200:
        def generate():
            for chunk in r.iter_content(chunk_size=1024):
                yield chunk
        return Response(generate(), content_type='video/MP2T')
    else:
        return Response(f"Error {r.status_code}: Unable to fetch the segment.", status=r.status_code)

@app.route('/<path:filename>')
def serve_public_files(filename):
    return send_from_directory('public', filename)

@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

if __name__ == '__main__':
    host = os.environ.get('INSTANCE_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 3000))
    app.run(host=host, port=port)
