import concurrent.futures
import logging
import os.path
import re
from datetime import datetime

from lxml.html import HTMLParser
from tzlocal import get_localzone

from .ComicInfo import ComicInfo
from .StreamLine import *

UTF8_PARSER = HTMLParser(encoding='utf-8')


class Lines:
    SYNC = 'SYNC'
    COMIC = 'COMIC'
    VOLUME = 'VOLUME'
    PAGE = 'PAGE'
    IMAGE = 'IMAGE'


class ComicDownloader:
    LOCAL_TZ = get_localzone()

    def __init__(self, host):
        self.__host = host

        self.__log = logging.getLogger("ComicDownloader")
        self.__connectTimeout = 10
        self.__downloadTimeout = 10

        self.__streamLinePool = StreamLinePool()
        self.__streamLinePool.add_stream_line(Lines.IMAGE, 200)
        self.__streamLinePool.add_stream_line(Lines.PAGE, 200)
        self.__streamLinePool.add_stream_line(Lines.VOLUME, 30)
        self.__streamLinePool.add_stream_line(Lines.COMIC)
        self.__streamLinePool.add_stream_line(Lines.SYNC)

    def search(self, params):
        return self.__host.search(params)

    def view(self, url):
        return self.__host.get_general_info({'url': url})

    def sync(self, comic_root_dir):
        self.__start_sync([{
            'save_dir': comic_root_dir
        }])

    def sync_all(self, root_dir):
        dirs = [os.path.join(root_dir, d) for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
        params = []
        for d in dirs:
            params.append({
                'save_dir': d
            })

        self.__start_sync(params)

    def __start_sync(self, params):
        self.__log.info("sync started.")
        line = self.__streamLinePool.get_stream_line(Lines.SYNC)
        for param in params:
            line.put(param)
        line.mark_end()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=100)
        for _ in range(min(len(params), 10)):
            executor.submit(self.__consume_sync_stream_line)
        for _ in range(min(len(params), 4)):
            executor.submit(self.__consume_comic_stream_line)
        for _ in range(3):
            executor.submit(self.__consume_volume_stream_line)
        for _ in range(17):
            executor.submit(self.__consume_page_stream_line)
        for _ in range(50):
            executor.submit(self.__consume_image_stream_line)
        executor.shutdown()
        self.__log.info("sync done!")

    def download(self, comic_params, mode):
        self.__log.info("download started. comics: %s" % len(comic_params))
        stream_line = self.__streamLinePool.get_stream_line(Lines.COMIC)
        for comic_param in comic_params:
            comic_param['download_mode'] = mode
            stream_line.put(comic_param)
        stream_line.mark_end()

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=100)

        for _ in range(min(len(comic_params), 3)):
            executor.submit(self.__consume_comic_stream_line)
        for _ in range(5):
            executor.submit(self.__consume_volume_stream_line)
        for _ in range(10):
            executor.submit(self.__consume_page_stream_line)
        for _ in range(60):
            executor.submit(self.__consume_image_stream_line)

        executor.shutdown()

    def __save_image(self, image_src, root, filename):
        target_file_path = os.path.join(root, filename)
        tmp_dir = os.path.join(root, ".downloadtmp")

        if os.path.isfile(root):
            os.remove(root)
        if not os.path.isdir(root):
            os.makedirs(root)
        if os.path.isfile(tmp_dir):
            os.remove(tmp_dir)
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)

        tmp_file_path = os.path.join(tmp_dir, filename)
        r = self.__host.request(image_src, stream=True, timeout=(self.__connectTimeout, self.__downloadTimeout))
        r.raise_for_status()
        isfile = os.path.isfile(target_file_path)
        if isfile and int(r.headers['Content-Length']) - os.stat(target_file_path).st_size == 0:
            return
        with open(tmp_file_path, 'wb') as f:
            r.raw.decode_content = True
            for chunk in r.iter_content(8192):
                f.write(chunk)
        os.rename(tmp_file_path, target_file_path)

    def __consume_sync_stream_line(self):
        sync_stream_line = self.__streamLinePool.get_stream_line(Lines.SYNC)
        comic_stream_line = self.__streamLinePool.get_stream_line(Lines.COMIC)
        task = None
        while True:
            try:
                with sync_stream_line:
                    task = sync_stream_line.take()
                    if task is StreamLine.EOQ:
                        if sync_stream_line.workerCount == 1:
                            comic_stream_line.mark_end()
                        break
                    sync_params = task.bundle
                    comic_root_dir = sync_params['save_dir']

                    comic_info = None

                    info_file_path = os.path.join(comic_root_dir, 'info.json')

                    if not os.path.exists(info_file_path):
                        self.__log.debug("no comic info was found.")
                        name = os.path.basename(comic_root_dir)
                        if name.isdigit():
                            # use it as ID
                            self.__log.info("use dirname as id: " + name)
                            comic_info = ComicInfo()
                            comic_info.title = name
                            comic_info.source = {
                                'id': int(name)
                            }
                        else:
                            self.__log.info("use dirname as search title: " + name)
                            search_result = self.__host.search(name)
                            if len(search_result) != 1:
                                self.__log.error(name + " has multiple search result. exit.")
                                continue

                            url = search_result[0]['url']
                            comic_info = ComicInfo()
                            comic_info.title = re.search('(\\d*).htm', url).group(1)
                            comic_info.source = {
                                'id': int(comic_info.title)
                            }
                    if comic_info is None:
                        with open(info_file_path) as file:
                            comic_info = ComicInfo.from_file(file)
                    if comic_info is None:
                        self.__log.error("invalid comic info file! exit.")
                        continue
                    if comic_info.finished and comic_info.has_synced():
                        comic_info.lastSyncTime = self.__get_current_dt_local()
                        ComicDownloader.__save_comic_info(comic_info, comic_root_dir)
                        continue
                    if 'id' not in comic_info.source and 'url' not in comic_info:
                        self.__log.error("invalid comic info %s: no [id] and [url]! exit." % comic_info.title)
                        continue
                    comic_url = self.__host.get_comic_url(comic_info.source)
                    html = self.__host.request_html(url=comic_url)
                    new_comic_info = self.__host.fetch_comic_info({
                        'html': html,
                        'url': comic_url
                    })

                    if not comic_info.is_outdated(new_comic_info.lastUpdateTime):
                        # update with new comic info
                        new_comic_info.lastSyncTime = self.__get_current_dt_local()
                        ComicDownloader.__save_comic_info(new_comic_info, comic_root_dir)
                        continue
                    comic_params = {
                        'save_dir': comic_root_dir,
                        'sub_dir': False,
                        'url': comic_url,
                        'html': html,
                        'comic_info': new_comic_info
                    }
                    comic_stream_line.put(comic_params)
            except Exception as e:
                self.__handle_consume_error(e, comic_stream_line.name, task)
            finally:
                self.__print_status()

    def __consume_comic_stream_line(self):
        comic_stream_line = self.__streamLinePool.get_stream_line(Lines.COMIC)
        volume_stream_line = self.__streamLinePool.get_stream_line(Lines.VOLUME)
        task = None
        while True:
            try:
                with comic_stream_line:
                    task = comic_stream_line.take()
                    if task is StreamLine.EOQ:
                        if comic_stream_line.workerCount == 1:
                            volume_stream_line.mark_end()
                        break
                    comic_params = task.bundle
                    # mode = comic_params['download_mode']

                    if 'html' not in comic_params:
                        comic_url = self.__host.get_comic_url(comic_params)
                        self.__log.info("fetching info from " + comic_url)
                        html = self.__host.request_html(comic_url)
                        comic_info = self.__host.fetch_comic_info({
                            'url': comic_url,
                            'html': html
                        })
                        comic_params['comic_info'] = comic_info
                        comic_params['html'] = html
                        if 'sub_dir' not in comic_params:
                            comic_params['sub_dir'] = True
                        ComicDownloader.__save_comic_info(comic_info, self.__get_comic_save_dir(comic_params))
                    else:
                        self.__log.info("add comic: " + comic_params['comic_info'].title)
                        if 'sub_dir' not in comic_params:
                            comic_params['sub_dir'] = True
                    volumes = self.__host.fetch_all_volumes(html=comic_params.get('html'), comic_params=comic_params)
                    if len(volumes) > 0:
                        volumes[-1]['last_one'] = True
                    for volume in volumes:
                        volume_stream_line.put(volume)
            except Exception as e:
                self.__log.error("consume.", e)
                self.__handle_consume_error(e, comic_stream_line.name, task)
            finally:
                self.__print_status()

    def __consume_volume_stream_line(self):
        volume_stream_line = self.__streamLinePool.get_stream_line(Lines.VOLUME)
        page_stream_line = self.__streamLinePool.get_stream_line(Lines.PAGE)
        task = None
        while True:
            try:
                with volume_stream_line:
                    task = volume_stream_line.take()
                    if task is StreamLine.EOQ:
                        if volume_stream_line.workerCount == 1:
                            page_stream_line.mark_end()
                        break
                    volume_params = task.bundle
                    volume_path = self.__get_volume_save_dir(volume_params)
                    db_folder = os.path.join(volume_path, ".finished")
                    already_downloaded = {}

                    if not os.path.isdir(db_folder):
                        os.makedirs(db_folder)
                    else:
                        for mark_file in os.listdir(db_folder):
                            already_downloaded[int(os.path.basename(mark_file))] = 1

                    page_params = self.__host.fetch_all_pages_from_volume(volume_params, already_downloaded)

                    if len(page_params) == 0 and 'last_one' in volume_params and volume_params['last_one']:
                        comic_info = volume_params['super']['comic_info']
                        comic_info.lastSyncTime = self.__get_current_dt_local()
                        ComicDownloader.__save_comic_info(comic_info, self.__get_comic_save_dir(volume_params['super']))
                        continue

                    if len(page_params) > 0:
                        page_params[-1]['last_one'] = True

                    for page_param in page_params:
                        page_stream_line.put(page_param)
            except Exception as e:
                self.__handle_consume_error(e, volume_stream_line.name, task)
            finally:
                self.__print_status()

    def __consume_page_stream_line(self):
        page_stream_line = self.__streamLinePool.get_stream_line(Lines.PAGE)
        image_stream_line = self.__streamLinePool.get_stream_line(Lines.IMAGE)
        task = None
        while True:
            try:
                with page_stream_line:
                    task = page_stream_line.take()
                    if task is StreamLine.EOQ:
                        if page_stream_line.workerCount == 1:
                            image_stream_line.mark_end()
                        break
                    page_params = task.bundle
                    for image_param in self.__host.fetch_all_images_from_page(page_params):
                        image_stream_line.put(image_param)
            except Exception as e:
                self.__handle_consume_error(e, page_stream_line.name, task)
            finally:
                self.__print_status()

    def __consume_image_stream_line(self):
        image_stream_line = self.__streamLinePool.get_stream_line(Lines.IMAGE)
        task = None
        while True:
            try:
                with image_stream_line:
                    task = image_stream_line.take()
                    if task is StreamLine.EOQ:
                        break
                    image_params = task.bundle
                    image_src = image_params['url']
                    page_params = image_params['super']
                    volume_params = page_params['super']
                    comic_params = volume_params['super']
                    target_dir = os.path.join(self.__get_volume_save_dir(volume_params))
                    index = page_params['index']
                    filename, file_extension = os.path.splitext(image_src)
                    self.__save_image(image_src, target_dir, "%s%s" % (index + 1, file_extension))
                    open(os.path.join(target_dir, ".finished", str(index)), 'w')

                    # update info.json when comic is downloaded
                    if 'last_one' in page_params and 'last_one' in volume_params:
                        comic_info = comic_params['comic_info']
                        comic_info.lastSyncTime = self.__get_current_dt_local()
                        ComicDownloader.__save_comic_info(comic_info, self.__get_comic_save_dir(comic_params))
            except Exception as e:
                self.__handle_consume_error(e, image_stream_line.name, task)
            finally:
                self.__print_status()

    def __handle_consume_error(self, e, line_name, task):
        # self.__log.error("failed!" + repr(task.bundle), e)
        if task is not None:
            stream_line = self.__streamLinePool.get_stream_line(line_name)
            if ComicDownloader.__error_can_retry(e):
                stream_line.put_error(task)
            else:
                self.__log.error("consume_" + line_name + " error!", e)
                stream_line.put_failed(task)

    def __print_status(self):
        self.__streamLinePool.print_status(self.__log)

    # noinspection PyUnusedLocal
    @staticmethod
    def __error_can_retry(e):
        return True
        # return isinstance(e, requests.exceptions.Timeout) or 'timed out' in str(e)

    @staticmethod
    def __save_comic_info(info, root_dir):
        if not os.path.isdir(root_dir):
            os.makedirs(root_dir)
        with open(os.path.join(root_dir, 'info.json'), 'w') as outfile:
            outfile.write(info.to_json())
        return info

    @staticmethod
    def __get_current_dt_local():
        return datetime.now().replace(tzinfo=ComicDownloader.LOCAL_TZ)

    @staticmethod
    def __get_volume_save_dir(volume_params):
        comic_info = volume_params['super']['comic_info']
        save_dir = volume_params['super']['save_dir']
        if volume_params['super'].get('sub_dir'):
            return os.path.join(save_dir, comic_info.title, volume_params['title'])
        else:
            return os.path.join(save_dir, volume_params['title'])

    @staticmethod
    def __get_comic_save_dir(comic_params):
        if comic_params.get('sub_dir'):
            return os.path.join(comic_params['save_dir'], comic_params['comic_info'].title)
        else:
            return comic_params['save_dir']


class Host:
    DIR_PATH = os.path.dirname(os.path.realpath(__file__))

    def __init__(self):
        pass

    def id(self):
        pass

    def request(self, url, *args):
        pass

    def request_html(self, url, *args):
        pass

    def request_raw(self, url, *args):
        pass

    def get_comic_url(self, params):
        pass

    def search(self, params):
        pass

    def get_general_info(self, params):
        pass

    def fetch_comic_info(self, comic_params):
        pass

    def fetch_all_volumes(self, html, comic_params):
        pass

    def fetch_all_pages_from_volume(self, volume_params, already_downloaded):
        pass

    def fetch_all_images_from_page(self, page_params):
        pass
