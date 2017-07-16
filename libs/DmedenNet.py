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
import logging

UTF8_PARSER = HTMLParser(encoding='utf-8')


class DmedenNetHost(Host):
    LOCAL_TZ = get_localzone()
    BASE_URL = "http://www.dmeden.net/"
    SEARCH_URL = "comic/?act=search"
    VOLUME_URL_TEMPLATE_REGEX = re.compile('ID=(\d*).*&s=(\d*)')
    PAGE_URL_TEMPLATE = "comichtml/%s/%s.html"
    VOLUME_URL_TEMPLATE = "comicinfo/%s.html"
    VIEW_JS_URL_REGEX = re.compile('src=\"(.*?)\"')
    VIEW_JS_FILE_PATH = Host.DIR_PATH + '/view.js'
    DATETIME_FORMAT = '%m/%d/%Y %I:%M:%S %p'

    HEADERS = {
        'Cookie': 'ASP.NET_SessionId=dpcatcjtjjh2rp55wnlf0xur'
    }

    def __init__(self):
        super().__init__()
        self.__viewJsCtx = None
        self.__viewJsCtxLock = Lock()
        self.__cookies = None
        self.__log = logging.getLogger("DmedenNet")

    def id(self):
        return 'dmeden.net'

    def get_comic_url(self, params):
        if 'id' in params and params['id']:
            return DmedenNetHost.BASE_URL + DmedenNetHost.VOLUME_URL_TEMPLATE % params['id']
        elif 'url' in params and params['url']:
            return DmedenNetHost.BASE_URL + params['url']
        raise Exception("get_comic_url failed! [id] or [url] is required!")

    def search(self, params):
        title = params['title']
        r = self.request_html(url=DmedenNetHost.BASE_URL + DmedenNetHost.SEARCH_URL, params={'st': title})
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
        volume_list = html('ul.cVolUl li a')
        for volumeEntry in volume_list:
            volumes.append({
                'title': volumeEntry.attrib['title'],
                'url': volumeEntry.attrib['href'],
                'super': comic_params
            })
        return volumes[::-1]

    def fetch_all_pages_from_volume(self, volume_params, already_downloaded):
        first_page_url = DmedenNetHost.BASE_URL + volume_params['url']
        reg = DmedenNetHost.VOLUME_URL_TEMPLATE_REGEX.search(first_page_url)
        key_id = reg.group(1)
        key_s = reg.group(2)
        first_page = self.request_html(url=DmedenNetHost.BASE_URL + DmedenNetHost.PAGE_URL_TEMPLATE % (key_id, 1),
                                       params={'s': key_s})

        total_pages = len(first_page('div#iPageHtm a'))

        i = 0

        result = []
        while i < total_pages:
            if already_downloaded.get(i) == 1:
                i += 1
                continue

            page_url = DmedenNetHost.BASE_URL + DmedenNetHost.PAGE_URL_TEMPLATE % (key_id, i + 1)
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
        dns_arr = r('input#hdDomain')[0].attrib['value']
        dns = dns_arr.split('|')[0]
        js_ctx = self.__get_view_js_context(r)
        with self.__viewJsCtxLock:
            image_src = js_ctx.unsuan(r('div img')[0].attrib['name'])

        return [{
            'url': dns + image_src,
            'super': page_params
        }]

    # noinspection PyBroadException
    def __get_view_js_context(self, page):
        with self.__viewJsCtxLock:
            if self.__viewJsCtx is not None:
                return self.__viewJsCtx
            if os.path.isfile(DmedenNetHost.VIEW_JS_FILE_PATH):
                with codecs.open(DmedenNetHost.VIEW_JS_FILE_PATH, "r", 'utf-8') as viewJsFile:
                    try:
                        self.__viewJsCtx = self.__create_js_context(viewJsFile.read())
                        return self.__viewJsCtx
                    except Exception as e:
                        os.remove(DmedenNetHost.VIEW_JS_FILE_PATH)
                        self.__log.error("failed to eval js: " + DmedenNetHost.VIEW_JS_FILE_PATH, e)
                        raise e
            text = page.html()
            view_js_url = DmedenNetHost.VIEW_JS_URL_REGEX.search(text).group(1)
            js_content = self.request_raw(DmedenNetHost.BASE_URL + view_js_url, None)
            with codecs.open(DmedenNetHost.VIEW_JS_FILE_PATH, "w", 'utf-8') as viewJsFile:
                viewJsFile.write(js_content)
            self.__viewJsCtx = self.__create_js_context(js_content)
            return self.__viewJsCtx

    def request(self, url, stream=False, params=None, timeout=10):
        self.__get_cookies()
        return requests.get(url=url, stream=stream, params=params, timeout=timeout, headers=DmedenNetHost.HEADERS, cookies=self.__cookies)

    def request_raw(self, url, params=None, stream=False, timeout=10):
        self.__get_cookies()
        r = requests.get(url=url, stream=stream, params=params, timeout=10, headers=DmedenNetHost.HEADERS, cookies=self.__cookies)
        r.encoding = 'utf-8'
        r.raise_for_status()
        return r.text

    def request_html(self, url, params=None, timeout=10, parser=UTF8_PARSER):
        self.__get_cookies()
        r = requests.get(url=url, params=params, timeout=timeout, headers=DmedenNetHost.HEADERS, cookies=self.__cookies)
        r.raise_for_status()
        return pyquery.PyQuery(fromstring(r.content, parser=parser))

    def __get_cookies(self):
        pass
        # r = requests.get(url=DmedenNetHost.BASE_URL)
        # self.__cookies = r.cookies

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
            info.finished = raw['狀態'] == '完结'
            info.rating = float(raw['評價'])

            info.lastUpdateTime = datetime.strptime(raw['更新'], DmedenNetHost.DATETIME_FORMAT)
            info.lastUpdateTime = info.lastUpdateTime.replace(tzinfo=DmedenNetHost.LOCAL_TZ)
            info.brief = raw['簡介']
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
        # 20170716 更新了一下解密算法，js里面，第一行用window属性的方式调用function，最终生成unsuan这个方法
        ctx.execute('''
        var location = {'hostname': 'www.dmeden.com'}
        var window = {
            'eval': eval,
            'String': String,
            'parseInt': parseInt,
            'RegExp': RegExp
        }
        ''')
        ctx.execute(js_content.split("\n", 1)[0])
        return ctx
