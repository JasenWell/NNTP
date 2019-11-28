# coding=utf-8

from abc import ABC, abstractmethod
from nntplib import NNTP, decode_header
from urllib.request import urlopen, urlretrieve
import re, textwrap
import argparse  # 处理命令行参数的库 Click为第三方命令行解析库更强大
import smtplib, email  # 发送电子邮件的库
import filecmp  # 文件对比库 difflib进行复杂的文件比较


# 管理工厂
class FactoryManager:
    def __init__(self):
        self.sourceFactory = SourceFactory()
        self.destinaFactory = DestinationFactory()
        self.sourceFactory.registerObserver(self.destinaFactory)
        pass

    def work(self):
        self.sourceFactory.product()
        pass


class InterfaceObserve(ABC):
    SEPARATE_LINE = '===================='

    def __init__(self):
        pass

    @abstractmethod
    def notifyDataChanged(self, news):
        pass


class NNTPDestination(InterfaceObserve):
    def __init__(self):
        super().__init__()

    def notifyDataChanged(self, news):
        for item in news:
            print(self.SEPARATE_LINE + 'begin show new' + self.SEPARATE_LINE)
            print(item.title)
            print(item.body)
            print(self.SEPARATE_LINE + 'end show new' + self.SEPARATE_LINE)


class HTMLDestination(InterfaceObserve):
    def __init__(self, fileName):
        super().__init__()
        self.fileName = fileName
        self.out = None

    def notifyDataChanged(self, news):
        self.out = open(self.fileName, 'w')
        self.out.write('<html>\n<head>\n<title>')
        self.out.write('{}</title>\n'.format("Today's News"))
        self.out.write('</head>\n</body>\n')
        self.out.write('<h1>{}</h1>\n'.format("Today's News"))
        self.out.write('<ul>\n')
        id = 0
        for item in news:
            id += 1
            self.out.write('<li><a href="#{}">{}</a></li>\n'.format(id, item.title))
        self.out.write('</ul>\n')
        id = 0
        for item in news:
            id += 1
            self.out.write('<h2><a name="{}">{}</a></h2>\n'.format(id, item.title))
            self.out.write('<pre>{}</pre>'.format(item.body))
        self.out.write('</body></html>')
        self.out.close()
        self.out = None


class XMLDestination(InterfaceObserve):
    def __init__(self, fileName):
        super().__init__()
        self.fileName = fileName
        self.out = None

    def notifyDataChanged(self, news):
        self.out = open(self.fileName, 'w')
        self.out.write('<website>\n<page name="{}" title="{}">\n'.format('home', 'Today\'s News'))
        self.out.write('<h1>{}</h1>\n'.format("Today's News"))
        for item in news:
            self.out.write('<h2>{}</h2>\n'.format(item.title))
            self.out.write('<pre>{}</pre>\n'.format(item.body))
        self.out.write('</page></website>')
        self.out.close()
        self.out = None


class AbstractFactory(ABC):
    SOURCE = 1
    DESTINATION = 2

    def __init__(self):
        self.type = 0
        pass

    @abstractmethod
    def product(self):
        pass


class DestinationFactory(AbstractFactory):
    def __init__(self):
        super().__init__()
        self.destinationList = []
        self.type = self.DESTINATION

    def product(self):
        pass

    def add(self, destination):
        self.destinationList.append(destination)


# 信息源工厂
class SourceFactory(AbstractFactory):

    def __init__(self):
        super().__init__()
        self.sourceList = []
        self.observeList = []
        self.type = self.SOURCE

    def add(self, source):
        self.sourceList.append(source)
        pass

    def registerObserver(self, observer):
        self.observeList.append(observer)
        pass

    def unregisterObserver(self, observer):
        self.observeList.remove(observer)

    def unregisterAllObserver(self):
        self.observeList.clear()

    def product(self):
        news = []
        for source in self.sourceList:
            method = getattr(source, source.getDisposeName(), None)
            try:
                items = list(source.getNewsItem())
            except Exception as e:
                continue
                pass
            news.extend(items)
            if callable(method):
                method(items)
        for destinationFactory in self.observeList:
            for destination in destinationFactory.destinationList:
                destination.notifyDataChanged(news)

        pass


class NewsItem:
    def __init__(self, title, body, type):
        self.title = title
        self.body = body
        self.sourceType = type


class Source(ABC):
    NNTP = 'NNTP'
    HTML = 'HTML'

    def __init__(self):
        self.type = ''
        pass

    @abstractmethod
    def getNewsItem(self):
        pass


class NNTPSource(Source):
    PREFIX = 'dispose'

    def __init__(self, serverName, group, howmany):
        super().__init__()
        self.serverName = serverName
        self.type = Source.NNTP
        self.group = group
        self.howmany = howmany
        self.server = NNTP(self.serverName)

    def getNewsItem(self):
        resp, count, first, last, name = self.server.group(self.group)
        resp = resp.split(' ')[0]
        if resp == '211':  # 正常响应
            start = last - self.howmany + 1
            resp, overviews = self.server.over((start, last))
            for id, over in overviews:
                title = decode_header(over['subject'])
                resp, info = self.server.body(id)
                body = '\n'.join(line.decode('latin') for line in info.lines) + '\n\n'  # 使用生成器推导,转字符串
                yield NewsItem(title, body, self.NNTP)
        else:
            yield None
        self.server.quit()

    def getDisposeName(self):
        return self.PREFIX + self.type
        pass

    def disposeNNTP(self, news):
        print('NNTP新闻生产完毕')
        pass


class HTMLSource(Source):
    PREFIX = 'dispose'

    def __init__(self, url, title_pattern, body_pattern, encoding='utf-8'):
        super().__init__()
        self.url = url
        self.title_pattern = re.compile(title_pattern)
        self.body_pattern = re.compile(body_pattern)
        self.encoding = encoding
        self.type = Source.HTML

    def getNewsItem(self):
        text = urlopen(self.url).read.decode(self.encoding)
        titles = self.title_pattern.findall(text)
        bodies = self.body_pattern.findall(text)
        for title, body in zip(titles, bodies):
            yield NewsItem(title, textwrap.fill(body) + '\n', self.HTML)
        pass

    def disposeHTML(self):
        print('HTML新闻生产完毕')

    def getDisposeName(self):
        return self.PREFIX + self.type
        pass


def startWork():
    manager = FactoryManager()
    # 可采用配置文件写入
    manager.sourceFactory.add(NNTPSource('news.gmane.org', 'gmane.comp.python.committers', 1))
    reuters_url = 'http://www.reuters.com/news/world'  # 路透社
    reuters_title = r'<h2><a href="[^"]*"\s*>(.*?)</a>'
    reuters_body = r'</h2><p>(.*?)</p>'
    manager.sourceFactory.add(HTMLSource(reuters_url, reuters_title, reuters_body))

    manager.destinaFactory.add(NNTPDestination())
    manager.destinaFactory.add(HTMLDestination('new.html'))
    manager.destinaFactory.add(XMLDestination('new.xml'))
    manager.work()


if __name__ == '__main__':
    startWork()
