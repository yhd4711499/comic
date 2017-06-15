import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import MapperExtension

Base = declarative_base()


def init_comic_db(engine):
    Base.metadata.create_all(engine)


class AutoUpdateTimestampExtension(MapperExtension):
    def before_update(self, mapper, connection, instance):
        instance.before_update()

    def before_insert(self, mapper, connection, instance):
        instance.before_insert()


class ComicBase:
    create_dt = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    update_dt = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def before_update(self):
        self.update_dt = datetime.datetime.utcnow()
        pass

    def before_insert(self):
        self.update_dt = self.create_dt = datetime.datetime.utcnow()
        pass

    __mapper_args__ = {
        'extension': AutoUpdateTimestampExtension()
    }


class SaveHistory(Base, ComicBase):
    __tablename__ = 'SaveHistory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    folder = Column(String, unique=True)

    @staticmethod
    def upsert(session, folder):
        item = session.query(SearchHistory).filter(SaveHistory.folder == folder).first()
        if item is None:
            item = SaveHistory(folder=folder)
        item.before_update()
        session.add(item)

    def __repr__(self):
        return '<SaveHistory(id=%s, folder=%s, timestamp=%s' % (self.id, self.folder, self.timestamp)


class SearchHistory(Base, ComicBase):
    __tablename__ = 'SearchHistory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String, unique=True)

    @staticmethod
    def upsert(session, keyword):
        item = session.query(SearchHistory).filter(SearchHistory.keyword == keyword).first()
        if item is None:
            item = SearchHistory(keyword=keyword)
        item.before_update()
        session.add(item)

    def __repr__(self):
        return '<SearchHistory(id=%s, keyword=%s, timestamp=%s' % (self.id, self.keyword, self.timestamp)
