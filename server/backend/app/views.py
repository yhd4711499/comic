import base64
import json
import os.path

from app import app
from flask import request
from flask import send_file
from flask import send_from_directory

configPath = '/Users/Ornithopter/Development/PycharmProjects/comic/default_config.json'

with open(configPath, encoding='utf-8') as file:
    config = json.loads(file.read())

comic_info_list = []
id_comic_dir_map = {}
id_comic_info_map = {}


@app.route('/')
@app.route('/index')
def index():
    return send_from_directory('../../frontend/dist/', 'index.html')


@app.route('/js/<path:path>')
def js(path):
    return send_from_directory('../../frontend/dist/js/', path)


@app.route('/css/<path:path>')
def css(path):
    return send_from_directory('../../frontend/dist/css/', path)


@app.route('/api/comics/all')
def get_comics():
    root_dir = os.path.expanduser(config['root_dir'])
    dir_list = os.listdir(root_dir)
    comic_info_list.clear()
    for comic_dir in dir_list:
        info_file = os.path.join(root_dir, comic_dir, 'info.json')
        if os.path.isfile(info_file):
            with open(info_file, encoding='utf-8') as file:
                content = file.read()
                comic_info_json = json.loads(content)
                comic_id = comic_info_json['source']['id']
                id_comic_dir_map[comic_id] = os.path.join(root_dir, comic_dir)
                id_comic_info_map[comic_id] = comic_info_json
                comic_info_list.append(content)
    return '[' + ','.join(comic_info_list) + ']'


@app.route('/api/comics/<string:comic_id>')
def get_volume_of_comic(comic_id):
    volumes = []
    comic_dir = id_comic_dir_map[comic_id]
    for volume_dir in os.listdir(comic_dir):
        if (not volume_dir.startswith('.')) and os.path.isdir(os.path.join(comic_dir, volume_dir)):
            volumes.append('{"title":"' + volume_dir + '"}')
    return '[' + ','.join(volumes) + ']'


@app.route('/api/comics/<string:comic_id>/<string:volume_id>')
def get_page_of_volume(comic_id, volume_id):
    pages = []
    comic_dir = id_comic_dir_map[comic_id]
    volume_dir = os.path.join(comic_dir, volume_id)
    host = 'http://' + request.host + '/'
    for img_file in os.listdir(volume_dir):
        img_file_abs = os.path.join(volume_dir, img_file)
        if (not img_file.startswith('.')) and os.path.isfile(img_file_abs):
            index = os.path.splitext(os.path.basename(img_file))[0]
            pages.append('{"url":"' + host + 'gtimg/' + base64.b64encode(img_file_abs.encode('utf-8')).decode(
                'utf-8') + '", "index":' + index + '}')
    return '[' + ','.join(pages) + ']'


@app.route('/gtimg/<path:src>')
def get_img(src):
    decode = base64.b64decode(src).decode('utf-8')
    return send_file(decode)


get_comics()
