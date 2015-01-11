import sys
import urllib2
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
	self.xml = response.read()
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
