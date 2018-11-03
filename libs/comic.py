import functools
import glob
import logging
import readline

from colorama import init
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .Dmeden import *
from .Stage import *
from .bcolors import *
from .entities import *


def print_results(results):
    for idx, r in enumerate(results):
        print("[%s] %s" % (idx, r['title']))


def complete(text, state):
    return (glob.glob(text + '*') + [None])[state]


def c(text, color):
    return color + str(text) + bcolors.ENDC


def cs(color, *texts):
    return tuple(map(functools.partial(c, color=color), texts))


init()
logging.basicConfig(level=logging.INFO, format='%(levelname)s/%(asctime)s - %(message)s')

readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(complete)

optionColor = bcolors.BOLD + bcolors.UNDERLINE


class ComicStage(Stage):
    engine = create_engine('sqlite:///' + os.path.dirname(os.path.realpath(__file__ + "/../")) + '/db', echo=False, encoding='utf-8')
    Session = sessionmaker(bind=engine)
    query_session = Session()

    def __init__(self, name):
        super().__init__(name)

    @staticmethod
    def create_session():
        return ComicStage.Session()

    @staticmethod
    def get_query():
        return ComicStage.query_session


class MainStage(ComicStage):
    """docstring for MainStage"""

    def __init__(self, downloader):
        super(MainStage, self).__init__("main")
        init_comic_db(ComicStage.engine)
        self.downloader = downloader

    def on_resume(self):
        print("===[ Welcome to Comic ]===")

    def on_turn_started(self):
        self.input = input("I want to: %search, %srowse, %suit : \n" % cs(optionColor, 's', 'b', 'q'))

    def on_response(self):
        if self.input == 's':
            self.change(SearchStage(self.downloader))

    def should_leave(self):
        return self.input == 'q'

    def on_leave(self):
        print("bye-bye")


class SearchStage(ComicStage):
    """docstring for SearchStage"""

    def __init__(self, downloader):
        super(SearchStage, self).__init__("search")
        self.downloader = downloader
        self.results = None

    def on_resume(self):
        print("===[ Search ]===")

    def on_turn_started(self):
        session = self.get_query()
        history = session.query(SearchHistory.keyword).order_by(SearchHistory.update_dt.desc()).limit(10)
        input_msg = "input title"
        default = None
        if history.count() != 0:
            default = history[0][0]
            for idx, folder in enumerate(history):
                print('[%s] %s' % (c(str(idx), optionColor), folder[0]))
            input_msg += ", leave blank to search [%s], or choose from history above: " % default

        input_msg += "\n"
        self.input = input(input_msg)
        if self.input.isdigit():
            self.input = history[int(self.input)][0]

        self.input = self.input or default

    def on_response(self):
        print("searching...")
        self.results = self.downloader.search({'title': self.input})

        session = self.create_session()
        SearchHistory.upsert(session, self.input)
        session.commit()

        self.change(SearchResultStage(self.downloader, self.results))

    def should_leave(self):
        return self.input == ""


# noinspection PyBroadException
class SearchResultStage(ComicStage):
    """docstring for SearchResultStage"""

    def __init__(self, downloader, results):
        super(SearchResultStage, self).__init__("SearchResultStage")
        self.downloader = downloader
        self.results = results

    def on_resume(self):
        print("===[ Search Results ]===")
        print_results(self.results)

    def on_turn_started(self):
        self.input = input("%sownload all, %sist, select [%s-%s], or %sack: \n"
                           % cs(optionColor, 'd', 'l', 0, len(self.results) - 1, 'b'))

    def on_response(self):
        try:
            index = int(self.input)
            if index >= len(self.results):
                return
            self.change(SearchResultDetailStage(self.downloader, index, self.results))
            return
        except Exception:
            pass

        if self.input == 'l':
            print_results(self.results)
        elif self.input == 'd':
            self.change(BatchDownloadStage(self.downloader, self.results))

    def should_leave(self):
        return self.input == 'b'


# noinspection PyBroadException
class SearchResultDetailStage(ComicStage):
    """docstring for SearchResultDetailStage"""

    def __init__(self, downloader, selected, results):
        super(SearchResultDetailStage, self).__init__("SearchResultDetailStage")
        self.downloader = downloader
        self.selected = selected
        self.results = results

    def print_detail(self, index):
        print("/**")
        for l in self.downloader.view(self.results[index]['url']):
            print(" * " + l)
        print(" */")

    def on_resume(self):
        print("===[ Search Result: %s ]===" % self.results[self.selected]['title'])
        self.print_detail(self.selected)

    def on_turn_started(self):
        self.input = input("%sownload, %sist all, select [%s-%s], or %sack: \n"
                           % cs(optionColor, 'd', 'l', '0', len(self.results) - 1, 'b'))
        try:
            index = int(self.input)
            if index >= len(self.results):
                return
            self.selected = index
            self.print_detail(index)
            return
        except Exception as e:
            pass

        if self.input == 'd':
            self.change(SingleDownloadStage(self.downloader, self.results[self.selected]))
        elif self.input == 'l':
            print_results(self.results)

    def should_leave(self):
        return self.input == 'b'


class SingleDownloadStage(ComicStage):
    """docstring for SingleDownloadStage"""

    def __init__(self, downloader, item):
        super(SingleDownloadStage, self).__init__("SingleDownloadStage")
        self.downloader = downloader
        self.item = item
        self.history = []

    def on_resume(self):
        print("===[ Download: %s ]===" % self.item['title'])

    def on_turn_started(self):
        session = self.get_query()
        history = session.query(SaveHistory.folder).order_by(SaveHistory.update_dt.desc()).limit(3)
        input_msg = "Where to save (leave blank to choose the first history):\n"
        default = None
        if history.count() != 0:
            default = history[0].folder
            for idx, folder in enumerate(history):
                print('[%s] %s' % (c(str(idx), optionColor), folder[0]))
            input_msg += "Or choose from history above."

        input_msg += "): \n"

        self.input = input(input_msg)
        if self.input.isdigit():
            self.input = history[int(self.input)]

        self.input = self.input or default

    def on_response(self):
        if not os.path.isdir(self.input):
            print("path is invalid!")
            return

        title = self.item['title']
        save_dir = self.input

        session = self.create_session()
        SaveHistory.upsert(session, save_dir)
        session.commit()

        # if save_dir.endswith('/'):
        #     save_dir += title

        s = input("[%s] will be saved to [%s]\npress %s to continue, or %sancel...\n"
                  % (c(title, bcolors.BOLD), c(os.path.abspath(save_dir), bcolors.BOLD), c("ENTER", optionColor),
                     c('c', optionColor)))
        if s != '':
            return
        self.downloader.download([{'save_dir': save_dir, 'url': self.item['url']}], 's')
        print("Download completed!")
        self.change(AfterDownloadCompleteStage(save_dir, self.item))

    def should_leave(self):
        return self.input == ''


class BatchDownloadStage(ComicStage):
    """docstring for BatchDownloadStage"""

    def __init__(self, downloader, items):
        super(BatchDownloadStage, self).__init__("BatchDownloadStage")
        self.downloader = downloader
        self.items = items

    def on_resume(self):
        print("===[ Batch Download: %s ]===" % len(self.items))

    def on_turn_started(self):
        self.input = input(
            "Where to save (leave blank to go back): \n")

    def on_response(self):
        if not os.path.isdir(self.input):
            print("path is invalid!")
            return

        s = input("%s comics will be saved to [%s]\npress %s to continue, or %sancel...\n"
                  % (c(len(self.items), bcolors.BOLD), c(os.path.abspath(self.input), bcolors.BOLD),
                     c("ENTER", optionColor), c('c', optionColor)))
        if s != '':
            return
        params = []
        for item in self.items:
            # title = item['title']
            save_dir = self.input
            # if save_dir.endswith('/'):
            #     save_dir += title
            params.append({
                'save_dir': save_dir,
                'url': item['url']
            })
        self.downloader.download(params, 'r')
        print("Download completed!")

        self.change(AfterBatchDownloadCompleteStage(s))

    def should_leave(self):
        return self.input == ''


class AfterDownloadCompleteStage(ComicStage):
    """docstring for AfterDownloadCompleteStage"""

    def __init__(self, save_dir, item):
        super(AfterDownloadCompleteStage, self).__init__("AfterDownloadCompleteStage")
        self.item = item
        self.saveDir = save_dir

    def on_resume(self):
        print("===[ Download Completed: %s ]===" % self.item['title'])

    def on_turn_started(self):
        self.input = input("[o]pen folder, blank to go back: ")

    def on_response(self):
        if self.input == 'o':
            import subprocess
            subprocess.call(["open", "-R", self.saveDir])

    def should_leave(self):
        return self.input == ''


class AfterBatchDownloadCompleteStage(ComicStage):
    """docstring for AfterDownloadCompleteStage"""

    def __init__(self, save_dir):
        super(AfterBatchDownloadCompleteStage, self).__init__("AfterBatchDownloadCompleteStage")
        self.saveDir = save_dir

    def on_resume(self):
        print("===[ Batch Download Completed %s ]===")

    def on_turn_started(self):
        self.input = input("[o]pen folder, blank to go back: ")

    def on_response(self):
        if self.input == 'o':
            import subprocess
            subprocess.call(["open", "-R", self.saveDir])

    def should_leave(self):
        return self.input == ''
