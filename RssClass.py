import sys
import urllib2
import HTMLParser
import xml.etree.ElementTree as ET
class Rss:
    """A class for handling RSS feeds"""
    def __init__(self):
        self.url = ""
        self.articles = []
	
    def __init__(self,url):
	self.url = url
        self.articles = []
    def get_rss_into_articles(self):
	response = urllib2.urlopen(self.url)
	self.xml = response.read().decode('utf-8')
	root = ET.fromstring(self.xml)

	for item in root.findall(".//item"):
            try:
	        title = item.find("title")
                link = item.find("link")
	        descr = item.find("description")
                pubDate = item.find("pubDate")
                strgDate = str(pubDate.text)
                article = Article(title.text,link.text,descr.text, strgDate)     
                self.articles.append(article)
            except: 
                print "Error in get_rss routine! Error report: ",sys.exc_info()[1]
        return self.articles



class Article:
    """A class for handling the details of an article"""
    def __init__(self):
        self.title = ''
        self.link = ''
        self.descr = ''
        self.pubDate = ''

    def __init__(self, title,link,descr,pubDate):
        self.title = title
        self.link = link
        self.descr = descr
        self.pubDate = pubDate
        self.full_txt = ''

    def get_full_txt(self):
        try:
            response = urllib2.urlopen(self.link).read().decode('utf-8')
            parser = RssHTMLParser()
            parser.feed(response)
            self.full_txt = parser.data
        except:
            print "Error in get_full_txt() of RssClass.Article", sys.exc_info()[1]

class RssHTMLParser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.is_start_p = False
        self.is_end_p = False
        self.data = ""
    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.is_start_p = True
        elif self.is_start_p and tag == 'a':
            self.is_start_p = True
        else:
            self.is_start_p = False

    def handle_endtag(self, tag):
        if tag == 'p':
            self.is_start_p = False
            self.is_end_p = True
        elif tag == 'a' and self.is_start_p:
            self.is_start_p = True
        else:
            self.is_end_p = False 

    def handle_data(self, data):
        if self.is_start_p:
            self.data += data
        elif self.is_end_p:
            self.data += ' '
