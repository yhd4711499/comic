import codecs
import logging
import os.path
import re
import urllib
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


class HuhudmHost(Host):
    LOCAL_TZ = get_localzone()
    BASE_URL = "http://www.huhudm.com/"
    SEARCH_URL = "comic/?act=search"
    VOLUME_URL_TEMPLATE_REGEX = re.compile('/(\d*)\.html')
    VOLUME_URL_TEMPLATE = "huhu%s.html"
    VIEW_JS_URL_REGEX = re.compile('src=\"(.*?)\"')
    VIEW_JS_FILE_PATH = Host.DIR_PATH + '/view.js'
    DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S'

    HEADERS = {}

    def __init__(self, config):
        super().__init__()
        self.__config = config or {}
        self.__proxy = None
        self.__viewJsCtx = None
        self.__viewJsCtxLock = Lock()
        self.__cookies = None
        self.__cookieGetLock = Lock()
        self.__log = logging.getLogger("huhudm")

    def id(self):
        return 'huhudm.com'

    def get_comic_url(self, params):
        if 'id' in params and params['id']:
            return HuhudmHost.BASE_URL + HuhudmHost.VOLUME_URL_TEMPLATE % params['id']
        elif 'url' in params and params['url']:
            return HuhudmHost.BASE_URL + params['url']
        raise Exception("get_comic_url failed! [id] or [url] is required!")

    def search(self, params):
        title = params['title']
        r = self.request_html(url=HuhudmHost.BASE_URL + HuhudmHost.SEARCH_URL, params={'st': title})
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
        first_page_url = HuhudmHost.BASE_URL + volume_params['url']
        first_page = self.request_html(url=first_page_url)

        total_pages = len(first_page('div#iPageHtm a'))

        i = 0

        result = []
        while i < total_pages:
            if already_downloaded.get(i) == 1:
                i += 1
                continue

            page_url = re.sub(HuhudmHost.VOLUME_URL_TEMPLATE_REGEX, "/%s.html" % (i + 1), first_page_url)
            page_params = {
                'url': page_url,
                'url_params': {},
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
            if os.path.isfile(HuhudmHost.VIEW_JS_FILE_PATH):
                with codecs.open(HuhudmHost.VIEW_JS_FILE_PATH, "r", 'utf-8') as viewJsFile:
                    try:
                        self.__viewJsCtx = self.__create_js_context(viewJsFile.read())
                        return self.__viewJsCtx
                    except Exception as e:
                        os.remove(HuhudmHost.VIEW_JS_FILE_PATH)
                        self.__log.error("failed to eval js: " + HuhudmHost.VIEW_JS_FILE_PATH, e)
                        raise e
            text = page.html()
            view_js_url = HuhudmHost.VIEW_JS_URL_REGEX.search(text).group(1)
            js_content = self.request_raw(HuhudmHost.BASE_URL + view_js_url, None)
            with codecs.open(HuhudmHost.VIEW_JS_FILE_PATH, "w", 'utf-8') as viewJsFile:
                viewJsFile.write(js_content)
            self.__viewJsCtx = self.__create_js_context(js_content)
            return self.__viewJsCtx

    def request(self, url, stream=False, params=None, timeout=10):
        self.__get_cookies()
        return requests.get(proxies=self.__proxy, url=url, stream=stream, params=params, timeout=timeout,
                            headers=HuhudmHost.HEADERS, cookies=self.__cookies)

    def request_raw(self, url, params=None, stream=False, timeout=10):
        self.__get_cookies()
        r = requests.get(proxies=self.__proxy, url=url, stream=stream, params=params, timeout=10,
                         headers=HuhudmHost.HEADERS, cookies=self.__cookies)
        r.encoding = 'utf-8'
        r.raise_for_status()
        return r.text

    def request_html(self, url, params=None, timeout=10, parser=UTF8_PARSER):
        self.__get_cookies()
        r = requests.get(proxies=self.__proxy, url=url, params=params, timeout=timeout, headers=HuhudmHost.HEADERS,
                         cookies=self.__cookies)
        r.raise_for_status()
        return pyquery.PyQuery(fromstring(r.content, parser=parser))

    def __get_cookies(self):
        with self.__cookieGetLock:
            if self.__cookies is None:
                if 'proxy' in self.__config:
                    proxy = self.__config['proxy']
                else:
                    proxy = None

                if proxy is None:
                    proxy = urllib.request.getproxies()
                elif not proxy['enabled']:
                    proxy = None
                r = requests.get(url=HuhudmHost.BASE_URL, proxies=proxy)
                HuhudmHost.HEADERS['Cookie'] = None
                self.__cookies = r.cookies
                if 'proxy_strategy' in self.__config and self.__config['proxy_strategy'] == 'ALL':
                    self.__proxy = proxy
                else:
                    self.__proxy = None

    @staticmethod
    def __parse_comic_info_from_raw(url, lines):
        info = ComicInfo()
        info.title = lines[0]
        info.source = {
            'host': 'huhudm.com',
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

            info.lastUpdateTime = datetime.strptime(raw['更新'], HuhudmHost.DATETIME_FORMAT)
            info.lastUpdateTime = info.lastUpdateTime.replace(tzinfo=HuhudmHost.LOCAL_TZ)
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
        # 20170716 更新了一下解密算法，js里面，第一行用window属性的方式调用function，最终生成unsuan这个方法
        ctx.execute('''
        var location = {'hostname': 'www.popomh.com'}
        var window = {
            'eval': eval,
            'String': String,
            'parseInt': parseInt,
            'RegExp': RegExp
        }
        ''')
        # todo: 只执行unsuan方法
        ctx.execute('\n'.join(js_content.split("\n", 30)[0:30]))
        return ctx
