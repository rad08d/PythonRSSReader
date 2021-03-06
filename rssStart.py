#!/usr/bin/env python
import sys
import os
import threading
from RssClass import Rss

try:
    dirName = os.path.dirname(__file__)
    path = os.path.join(dirName,  "rssWebSites.txt")
    with open(path) as file:
        sites = file.readlines()
    print len(sites)
    siteStories = []
    for site in sites:
        rss = Rss(site)
        rss.get_rss_into_articles()
	siteStories.append(rss)
except IOError: 
    print "Can't find website list file. Error: " , sys.exc_info()[1]

for collArticles in siteStories:
    print collArticles.url, "\n"
    for article in collArticles.articles:
        print article.title, "\n", article.pubDate, "\n\n"
