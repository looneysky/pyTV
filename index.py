import os
import requests
import subprocess
from flask import Flask, request, Response

app = Flask(__name__)

BASE_URL = 'http://cdntv.online/hls/46t9msx5cz'

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

@app.route('/invalid_key_segment')
def serve_invalid_key_segment():
    def generate():
        with open(INVALID_KEY_SEGMENT, 'rb') as f:
            while chunk := f.read(1024):
                yield chunk
    return Response(generate(), content_type='video/MP2T')

def generate_invalid_key_playlist():
    return f"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
http://{os.environ.get("INSTANCE_HOST")}:{os.environ.get("PORT")}/invalid_key_segment
#EXTINF:10.0,
http://{os.environ.get("INSTANCE_HOST")}:{os.environ.get("PORT")}/invalid_key_segment
#EXTINF:10.0,
http://{os.environ.get("INSTANCE_HOST")}:{os.environ.get("PORT")}/invalid_key_segment
#EXTINF:10.0,
http://{os.environ.get("INSTANCE_HOST")}:{os.environ.get("PORT")}/invalid_key_segment
#EXTINF:10.0,
http://{os.environ.get("INSTANCE_HOST")}:{os.environ.get("PORT")}/invalid_key_segment
"""

@app.route('/<path:path>')
def invalid_key_response(path):
    invalid_key_playlist = generate_invalid_key_playlist()
    return Response(invalid_key_playlist, content_type='application/vnd.apple.mpegurl')

if __name__ == '__main__':
    host = os.environ.get('INSTANCE_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 3000))
    app.run(host=host, port=port)
