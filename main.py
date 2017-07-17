import json
import sys
from optparse import OptionParser, OptionGroup

from libs import *


def main():
    usage = "usage: %prog [options] arg"

    parser = OptionParser(usage=usage)

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="print a lot of logs")

    parser.add_option("-s", "--source", dest="source",
                      help="set source", default='dmeden.net')

    parser.add_option("--cli", "--cli", action="store_true", dest="cli",
                      help="enter cli mode")

    parser.add_option("-c", "--conf", dest="config_path", default="default.json", help="load config file")

    download_group = OptionGroup(parser, "Download Options", "Download comic by its relative url or id.")

    download_group.add_option("-i", "--id", dest="id",
                              help="download comic with ID")

    download_group.add_option("-u", "--url", dest="url",
                              help="download comic from relative url")

    download_group.add_option("-m", "--mode", dest="mode", default='r',
                              help="download mode. [s]equntial or [r]andom. (default is 'r')")

    parser.add_option_group(download_group)

    search_group = OptionGroup(parser, "Search Options", "Search comics.")

    search_group.add_option("--st", "--search_title", dest="search_title", metavar="TITLE",
                            help="search by title")

    parser.add_option_group(search_group)

    manage_group = OptionGroup(parser, "Manage Options", "Mange comics.")

    manage_group.add_option("--up", "--update", dest="update_one", metavar="COMIC_DIR",
                            help="Update local comic of COMIC_DIR")

    manage_group.add_option("--up_all", "--update_all", dest="update_all", metavar="ROOT_DIR",
                            help="Update all local comics under ROOT_DIR")

    parser.add_option_group(manage_group)

    (options, args) = parser.parse_args()

    downloader = None
    config = None

    if options.config_path and os.path.isfile(options.config_path):
        with open(options.config_path, encoding='utf-8') as file:
            config = json.loads(file.read())
            if 'root_dir' in config and len(args) == 0:
                args = [config['root_dir']]
            if 'source' in config and options.source is None:
                options.source = config['source']

    sources = [DmedenHost(config), Dm5Host(config), DmedenNetHost(config)]

    if options.source:
        for source in sources:
            if source.id() == options.source:
                downloader = ComicDownloader(source)

    if downloader is None:
        print("can't find source for: " + str(options.source))
        sys.exit(2)

    level = logging.INFO
    if options.verbose:
        level = logging.DEBUG
    logging.basicConfig(level=level, format='%(levelname)s/%(asctime)s - %(message)s')

    if len(args) == 1 or options.cli:
        ctx = Context()
        MainStage(downloader).enter(ctx)
        return

    if options.id is not None or options.url is not None:
        if len(args) == 0:
            print("error: output dir is missing!")
            sys.exit(2)
        downloader.download([{'save_dir': args[0], 'id': options.id, 'url': options.url}], options.mode)
        return

    if options.search_title is not None:
        downloader.search({
            'title': options.search_title
        })
        return

    if options.update_one is not None:
        downloader.sync(options.update_one)
        return

    if options.update_all is not None:
        downloader.sync_all(options.update_all)
        return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        hour = datetime.datetime.now(tz=get_localzone()).hour
        if hour > 19:
            print("bye-bye. Have a good day.")
        else:
            print("bye-bye. Have a good night.")
