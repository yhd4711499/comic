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


@app.route('/api/comics/<string:action>/<string:comic_id>/<path:volume_id>')
def get_sidling_volume(action, comic_id, volume_id):
    volume_id = from_base64(volume_id)
    comic_dir = id_comic_dir_map[comic_id]
    found = False
    last_volume_dir = None
    for volume_dir in os.listdir(comic_dir):
        if volume_dir == volume_id:
            found = True
            continue
        if found:
            if action == 'next':
                return get_page_of_volume(comic_id, to_base64(volume_dir))
            elif action == 'previous' and last_volume_dir is not None:
                return get_page_of_volume(comic_id, to_base64(last_volume_dir))
            else:
                break
        if os.path.isdir(os.path.join(comic_dir, volume_dir)):
            last_volume_dir = volume_dir
    return json.dumps({})


@app.route('/api/comics/<string:comic_id>/<path:volume_id>')
def get_page_of_volume(comic_id, volume_id):
    volume_title = from_base64(volume_id)
    pages = []
    comic_dir = id_comic_dir_map[comic_id]
    volume_dir = os.path.join(comic_dir, volume_title)
    host = 'http://' + request.host + '/'
    for img_file in os.listdir(volume_dir):
        img_file_abs = os.path.join(volume_dir, img_file)
        if (not img_file.startswith('.')) and os.path.isfile(img_file_abs):
            index = int(os.path.splitext(os.path.basename(img_file))[0])
            pages.append({
                "url": host + 'gtimg/' + to_base64(img_file_abs),
                "index": index
            })
    return json.dumps({
        'title': volume_title,
        'id': volume_id,
        'images': pages
    })


@app.route('/api/comics/<string:comic_id>')
def get_volume_of_comic(comic_id):
    volumes = []
    comic_dir = id_comic_dir_map[comic_id]
    comic_info = id_comic_info_map[comic_id]
    for volume_dir in os.listdir(comic_dir):
        if (not volume_dir.startswith('.')) and os.path.isdir(os.path.join(comic_dir, volume_dir)):
            volumes.append({"title": volume_dir, "id": to_base64(volume_dir)})
    return json.dumps({
        'comic_info': comic_info,
        'volumes': volumes
    })


@app.route('/gtimg/<path:src>')
def get_img(src):
    decode = from_base64(src)
    return send_file(decode)


def to_base64(src):
    return base64.b64encode(src.encode('utf-8')).decode('utf-8')


def from_base64(src):
    return base64.b64decode(src).decode('utf-8')


get_comics()
