import json
from datetime import datetime

import pytz
from tzlocal import get_localzone


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        # save in UTC
        serial = obj.astimezone(pytz.utc).strftime(ComicInfo.ISO_FORMAT)
        return serial
    return obj.__dict__


class ComicInfo(object):
    """docstring for ComicInfo"""

    ISO_FORMAT = '%Y-%m-%dT%H:%M:%S'

    LOCAL = get_localzone()

    def __init__(self):
        super(ComicInfo, self).__init__()
        self.title = None
        self.finished = False
        self.author = None
        # UTC
        self.lastUpdateTime = None
        # UTC
        self.lastSyncTime = None
        self.rating = 0.0
        self.brief = None
        self.source = None

    def has_synced(self):
        if hasattr(self, 'lastSyncTime'):
            return self.lastSyncTime is not None
        return False

    def is_outdated(self, last_update_time):
        if last_update_time is None:
            return True
        if not hasattr(self, 'lastSyncTime'):
            return True
        if self.lastSyncTime is None:
            return True
        return self.lastSyncTime < last_update_time

    @classmethod
    def from_file(cls, json_file):
        info = cls()
        info.__dict__ = json.loads(json_file.read())
        if hasattr(info, 'lastUpdateTime') and info.lastUpdateTime is not None:
            info.lastUpdateTime = datetime.strptime(info.lastUpdateTime, ComicInfo.ISO_FORMAT).replace(tzinfo=pytz.utc)
        if hasattr(info, 'lastSyncTime') and info.lastSyncTime is not None:
            info.lastSyncTime = datetime.strptime(info.lastSyncTime, ComicInfo.ISO_FORMAT).replace(tzinfo=pytz.utc)
        return info

    def to_json(self):
        return json.dumps(self, default=json_serial, sort_keys=True, indent=4, ensure_ascii=False)
