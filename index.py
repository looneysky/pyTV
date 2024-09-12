import os
import re
import requests
from flask import Flask, request, Response, send_from_directory

app = Flask(__name__)

BASE_URL = 'http://cdntv.online/hls/46t9msx5cz'
SEGMENT_BASE_URL_PATTERN = r"http://r\d+\.cdntv\.online/hls/46t9msx5cz/(\d+)/([^\s]+)"  # Regex to match the full URL

def get_subdomain_for_url(url):
    # Extract the subdomain from the URL
    match = re.match(r"http://(r\d+)\.cdntv\.online", url)
    if match:
        return match.group(1)
    return 'r1'  # Default subdomain if extraction fails

@app.route('/tv/<id>.m3u8')
def relay_playlist(id):
    query_string = request.query_string.decode("utf-8")
    url = f'{BASE_URL}/{id}.m3u8?{query_string}'

    instance_host = os.environ.get("INSTANCE_HOST", '192.168.0.106')
    port = os.environ.get("PORT", '3001')

    try:
        r = requests.get(url)
        r.raise_for_status()  # Raise an exception for HTTP errors
    except requests.RequestException as e:
        app.logger.error(f"Error fetching playlist: {e}")
        return Response(f"Error fetching playlist: {e}", status=500)

    content = r.text

    # Log original playlist content for debugging
    app.logger.debug(f"Original playlist content:\n{content}")

    # Modify playlist content
    modified_content = re.sub(
        SEGMENT_BASE_URL_PATTERN,
        lambda match: f'http://{instance_host}:{port}/segments/{get_subdomain_for_url(match.group(0))}/{match.group(1)}/{match.group(2)}',
        content
    )

    # Log modified playlist content for debugging
    app.logger.debug(f"Modified playlist content:\n{modified_content}")

    return Response(modified_content, content_type='application/vnd.apple.mpegurl')

@app.route('/segments/<subdomain>/<id>/<path:segment>')
def relay_segment(subdomain, id, segment):
    # Construct the URL for fetching the original segment
    original_url = f'http://{subdomain}.cdntv.online/hls/46t9msx5cz/{id}/{segment}'
    app.logger.info(f"Fetching segment from URL: {original_url}")

    try:
        r = requests.get(original_url, stream=True)
        r.raise_for_status()  # Raise an exception for HTTP errors
    except requests.RequestException as e:
        app.logger.error(f"Error fetching segment: {e}")
        return Response(f"Error fetching segment: {e}", status=500)

    # Check if the content length is zero
    content_length = r.headers.get('Content-Length')
    app.logger.info(f"Downloading segment {segment} with length {content_length}")

    if content_length and int(content_length) == 0:
        app.logger.warning("Segment content length is 0, skipping save.")
        return Response("Segment content length is 0, skipping save.", status=204)  # Return 204 No Content

    # Directly stream the content without saving to disk
    def generate():
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                yield chunk

    return Response(generate(), content_type='video/MP2T')

@app.route('/<path:filename>')
def serve_public_files(filename):
    return send_from_directory('public', filename)

@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

if __name__ == '__main__':
    host = os.environ.get('INSTANCE_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 3001))
    app.run(host=host, port=port, debug=True)
