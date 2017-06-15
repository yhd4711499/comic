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


def reverse(queue):
    left = 0
    right = queue_length(queue) - 1

    while left < right:
        swap(queue, left, right)
        left += 1
        right -= 1


class DmedenHost(Host):
    LOCAL_TZ = get_localzone()
    BASE_URL = "http://www.dmeden.com/"
    SEARCH_URL = "comic/?act=search"
    VOLUME_URL_TEMPLATE_REGEX = re.compile('ID=(\d*).*&s=(\d*)')
    PAGE_URL_TEMPLATE = "comichtml/%s/%s.html"
    VOLUME_URL_TEMPLATE = "comicinfo/%s.html"
    VIEW_JS_URL_REGEX = re.compile('src=\"(.*?)\"')
    VIEW_JS_FILE_PATH = Host.DIR_PATH + '/view.js'
    DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S'

    def __init__(self):
        super().__init__()
        self.__viewJsCtx = None
        self.__viewJsCtxLock = Lock()

    def id(self):
        return 'dmeden.com'

    def get_comic_url(self, params):
        if 'id' in params and params['id']:
            return DmedenHost.BASE_URL + DmedenHost.VOLUME_URL_TEMPLATE % params['id']
        elif 'url' in params and params['url']:
            return DmedenHost.BASE_URL + params['url']
        raise Exception("get_comic_url failed! [id] or [url] is required!")

    def search(self, params):
        title = params['title']
        r = self.request_html(url=DmedenHost.BASE_URL + DmedenHost.SEARCH_URL, params={'st': title})
        result = []
        for comicEntry in r('div.cComicList a'):
            result.append({
                'title': comicEntry.attrib['title'],
                'url': comicEntry.attrib['href']
            })
        return result

    def get_general_info(self, params):
        url = self.get_comic_url(params)
        r = self.request_html(url=url)
        about_div = r('div#about_kit')
        return self.__get_raw_comic_info(about_div.html())

    def fetch_comic_info(self, comic_params):
        html = comic_params['html']
        url = comic_params['url']
        if not html:
            html = self.request_html(url=url)
        return self.__parse_comic_info_from_raw(url, self.__get_raw_comic_info(html('div#about_kit').html()))

    def fetch_all_volumes(self, html, comic_params):
        volumes = []
        volume_list = html('ul.list_s li a')
        for volumeEntry in volume_list:
            volumes.append({
                'title': volumeEntry.attrib['title'],
                'url': volumeEntry.attrib['href'],
                'super': comic_params
            })
        return volumes[::-1]

    def fetch_all_pages_from_volume(self, volume_params, already_downloaded):
        first_page_url = DmedenHost.BASE_URL + volume_params['url']
        reg = DmedenHost.VOLUME_URL_TEMPLATE_REGEX.search(first_page_url)
        key_id = reg.group(1)
        key_s = reg.group(2)
        first_page = self.request_html(url=DmedenHost.BASE_URL + DmedenHost.PAGE_URL_TEMPLATE % (key_id, 1),
                                       params={'s': key_s})

        total_pages = len(first_page('div#iPageHtm a'))

        i = 0

        result = []
        while i < total_pages:
            if already_downloaded[i] == 1:
                i += 1
                continue

            page_url = DmedenHost.BASE_URL + DmedenHost.PAGE_URL_TEMPLATE % (key_id, i + 1)
            page_params = {
                'url': page_url,
                'url_params': {'s': key_s},
                'index': i,
                'super': volume_params
            }
            result.append(page_params)
            i += 1

        if len(result) > 0:
            result[len(result) - 1]['last_one'] = True

        return result

    def fetch_all_images_from_page(self, page_params):
        r = self.request_html(url=page_params['url'], params=page_params['url_params'])
        js_ctx = self.__get_view_js_context(r)
        with self.__viewJsCtxLock:
            image_src = js_ctx.unsuan(r('img#imgCurr')[0].attrib['name'])

        return [{
            'url': image_src,
            'super': page_params
        }]

    # noinspection PyBroadException
    def __get_view_js_context(self, page):
        with self.__viewJsCtxLock:
            if self.__viewJsCtx is not None:
                return self.__viewJsCtx
            if os.path.isfile(DmedenHost.VIEW_JS_FILE_PATH):
                with codecs.open(DmedenHost.VIEW_JS_FILE_PATH, "r", 'utf-8') as viewJsFile:
                    try:
                        self.__viewJsCtx = self.__create_js_context(viewJsFile.read())
                        return self.__viewJsCtx
                    except Exception:
                        os.remove(DmedenHost.VIEW_JS_FILE_PATH)
            text = page.html()
            view_js_url = DmedenHost.VIEW_JS_URL_REGEX.search(text).group(1)
            js_content = self.request_raw(DmedenHost.BASE_URL + view_js_url, None)
            with codecs.open(DmedenHost.VIEW_JS_FILE_PATH, "w", 'utf-8') as viewJsFile:
                viewJsFile.write(js_content)
            self.__viewJsCtx = self.__create_js_context(js_content)
            return self.__viewJsCtx

    def request(self, url, stream=False, params=None, timeout=10):
        return requests.get(url=url, stream=stream, params=params, timeout=timeout)

    def request_raw(self, url, params=None, stream=False, timeout=10):
        r = requests.get(url=url, stream=stream, params=params, timeout=10)
        r.encoding = 'utf-8'
        r.raise_for_status()
        return r.text

    def request_html(self, url, params=None, timeout=10, parser=UTF8_PARSER):
        r = requests.get(url=url, params=params, timeout=timeout)
        r.raise_for_status()
        return pyquery.PyQuery(fromstring(r.content, parser=parser))

    @staticmethod
    def __parse_comic_info_from_raw(url, lines):
        info = ComicInfo()
        info.title = lines[0]
        info.source = {
            'host': 'dmeden',
            'id': re.search('(\\d*).htm', url).group(1)
        }
        try:
            raw = {}
            for line in lines[1:]:
                parts = re.split(" *: *", line, 1)
                if len(parts) == 2:
                    raw[parts[0]] = parts[1]
            info.author = raw['作者']
            info.finished = raw['状态'] == '完结'
            info.rating = float(raw['评价'])

            info.lastUpdateTime = datetime.strptime(raw['更新'], DmedenHost.DATETIME_FORMAT)
            info.lastUpdateTime = info.lastUpdateTime.replace(tzinfo=DmedenHost.LOCAL_TZ)
            info.brief = raw['简介']
        except Exception as e:
            print(e)
        return info

    @staticmethod
    def __get_raw_comic_info(html):
        s = re.sub('</[^b]*>', '\n', html)
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
