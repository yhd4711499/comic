import codecs
import os.path
import re
from datetime import datetime

import js2py
import pyquery
import requests
from lxml.html import HTMLParser, fromstring
from tzlocal import get_localzone

from libs.comic_downloader import Host
from .ComicInfo import ComicInfo
from .StreamLine import *

UTF8_PARSER = HTMLParser(encoding='utf-8')


def request_raw(url, params=None):
    r = requests.get(url=url, params=params, timeout=10)
    r.encoding = 'utf-8'
    r.raise_for_status()
    return r.text


def request_html(url, params=None, timeout=10, parser=UTF8_PARSER):
    r = requests.get(url=url, params=params, timeout=timeout)
    r.raise_for_status()
    return pyquery.PyQuery(fromstring(r.content, parser=parser))


def reverse(queue):
    left = 0
    right = queue_length(queue) - 1

    while left < right:
        swap(queue, left, right)
        left += 1
        right -= 1


class Dm5Host(Host):
    LOCAL_TZ = get_localzone()
    BASE_URL = "http://www.dm5.com/"
    SEARCH_URL = "search/?language=1"
    VOLUME_URL_TEMPLATE_REGEX = re.compile('ID=(\d*).*&s=(\d*)')
    PAGE_URL_TEMPLATE = "comichtml/%s/%s.html"
    VOLUME_URL_TEMPLATE = "comicinfo/%s.html"
    VIEW_JS_URL_REGEX = re.compile('src=["\'](.*chapternew.*js)[\'"]')
    VIEW_JS_FILE_PATH = Host.DIR_PATH + '/dm5chapternew.js'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        super().__init__()
        self.__viewJsCtx = None
        self.__viewJsCtxLock = Lock()

    def id(self):
        return 'dm5'

    def get_comic_url(self, params):
        if params.get('id'):
            return Dm5Host.BASE_URL + Dm5Host.VOLUME_URL_TEMPLATE % params['id']
        elif params['url']:
            return Dm5Host.BASE_URL + params['url']
        raise Exception("get_comic_url failed! [id] or [url] is required!")

    def search(self, params):
        title = params['title']
        r = request_html(url=Dm5Host.BASE_URL + Dm5Host.SEARCH_URL, params={'title': title})
        result = []
        for comicEntry in r('div.midBar a.title'):
            result.append({
                'title': comicEntry.text,
                'url': comicEntry.attrib['href']
            })
        return result

    def get_general_info(self, params):
        url = self.get_comic_url(params)
        r = request_html(url=url)
        about_div = r('div.innr90')
        return self.__get_raw_comic_info(about_div.html())

    def fetch_comic_info(self, comic_params):
        url = comic_params['url']
        if 'html' in comic_params:
            html = comic_params['html']
        else:
            html = request_html(url=Dm5Host.BASE_URL + url)
        return self.__parse_comic_info_from_raw(url, self.__get_raw_comic_info(html('div.innr90').html()))

    def fetch_all_volumes(self, html, comic_params):
        volumes = []
        first_page_url = html('a#bt_shownext')[0].attrib['href']
        first_page_html = request_html(first_page_url)
        list_of_volume_list = first_page_html('div.list.l1.iList')
        for volume_list in list_of_volume_list:
            for volumeEntry in pyquery.PyQuery(volume_list)('a'):
                url = volumeEntry.attrib['href']
                cid = re.match('.*/m(.*)/', url).group(1)
                volumes.append({
                    'cid': cid,
                    'title': volumeEntry.text,
                    'url': volumeEntry.attrib['href'],
                    'super': comic_params
                })

        return volumes

    def fetch_all_pages_from_volume(self, volume_params, already_downloaded):
        first_page_url = Dm5Host.BASE_URL + volume_params['url']
        cid = volume_params['cid']
        comic_params = volume_params['super']
        volume_path = os.path.join(comic_params['save_dir'], volume_params['title'])
        first_page = request_html(first_page_url, None)

        total_pages = len(first_page('div.pageBar.bar.down.iList a'))
        i = 0
        db_folder = os.path.join(volume_path, ".finished")
        need_download = [0] * total_pages

        if not os.path.isdir(db_folder):
            os.makedirs(db_folder)
            need_download = [1] * total_pages
        else:
            while i < total_pages:
                mark_file = os.path.join(db_folder, str(i))
                if not os.path.isfile(mark_file):
                    need_download[i] = 1
                i += 1
            i = 0

        result = []
        while i < total_pages:
            if need_download[i] == 0:
                i += 1
                continue

            page_url = first_page_url.replace(cid, cid + '-p' + str(i+1))
            page_params = {
                'url': page_url,
                'index': i,
                'super': volume_params
            }
            result.append(page_params)
            i += 1

        if len(result) > 0:
            result[len(result) - 1]['last_one'] = True

        return result

    def fetch_all_images_from_page(self, page_params):
        # r = request_html(url=page_params['url'])
        cid = page_params['super']['cid']
        js_fun = requests.get(Dm5Host.BASE_URL + 'chapterfun.ashx', {
            'cid': cid,
            'page': page_params['index'] + 1,
            'language': 1,
            'gtk': 6,
            'mkey': ''
        }).content
        js_ctx = js2py.EvalJs({})
        js_ctx.eval(js_fun)
        image_src = js_ctx.d[0]
        # js_ctx = self.__get_view_js_context(r)
        # with self.__viewJsCtxLock:
        #     image_src = js_ctx.unsuan(r('img#imgCurr')[0].attrib['name'])

        return [{
            'url': image_src,
            'super': page_params
        }]

    # noinspection PyBroadException
    def __get_view_js_context(self, page):
        with self.__viewJsCtxLock:
            if self.__viewJsCtx is not None:
                return self.__viewJsCtx
            if os.path.isfile(Dm5Host.VIEW_JS_FILE_PATH):
                with codecs.open(Dm5Host.VIEW_JS_FILE_PATH, "r", 'utf-8') as viewJsFile:
                    try:
                        self.__viewJsCtx = self.__create_js_context(viewJsFile.read())
                        return self.__viewJsCtx
                    except Exception:
                        os.remove(Dm5Host.VIEW_JS_FILE_PATH)
            text = page.html()
            view_js_url = Dm5Host.VIEW_JS_URL_REGEX.search(text).group(1)
            js_content = request_raw(Dm5Host.BASE_URL + view_js_url, None)
            with codecs.open(Dm5Host.VIEW_JS_FILE_PATH, "w", 'utf-8') as viewJsFile:
                viewJsFile.write(js_content)
            self.__viewJsCtx = self.__create_js_context(js_content)
            return self.__viewJsCtx

    @staticmethod
    def __parse_comic_info_from_raw(url, lines):
        info = ComicInfo()
        info.title = lines[0]
        info.source = {
            'host': 'dmeden',
            'id': url
        }
        try:
            raw = {}
            for line in lines[1:]:
                parts = re.split(" *:*", line, 1)
                if len(parts) == 2:
                    raw[parts[0]] = parts[1]
            info.author = raw['漫画作者']
            info.finished = raw['漫画状态'] != '连载'
            info.rating = float(raw['评价'])

            info.lastUpdateTime = datetime.strptime(raw['更新时间'], Dm5Host.DATETIME_FORMAT)
            info.lastUpdateTime = info.lastUpdateTime.replace(tzinfo=Dm5Host.LOCAL_TZ)
        except Exception as e:
            print(e)
        return info

    @staticmethod
    def __get_raw_comic_info(html):
        s = re.sub('</span>', '\n', html)
        s = re.sub('<[/]?\\w*>', '', s)
        s = re.sub('<.*?>', '', s)
        s = re.sub('&#\d*;', '', s)
        s = s.split('\n')
        s = [l.strip() for l in s if l.strip()]
        return s

    @staticmethod
    def __create_js_context(js_content):
        ctx = js2py.EvalJs({})
        ctx.execute('''
    var location = {'hostname': 'www.dmeden.com'}
    ''')
        ctx.execute(js_content)
        return ctx


