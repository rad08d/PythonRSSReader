import urllib2
import xml.etree.ElementTree as ET
print "Script start: "


urlGoo = "http://9to5google.com/feed/"
responseGoo = urllib2.urlopen(urlGoo)

urlMac = "http://9to5mac.com/feed/"
responseMac = urllib2.urlopen(urlMac)


xmlGoo = responseGoo.read()
rootGoo = ET.fromstring(xmlGoo)

xmlMac = responseMac.read()
rootMac = ET.fromstring(xmlMac)


for item in rootMac.findall(".//item"):
	title = item.find("title")
	descr = item.find("description")
	print title.text + "\n\n", descr.text + "\n\n\n"

for item in rootGoo.findall(".//item"):
	title = item.find("title")
	descr = item.find("description")
	print title.text + "\n\n", descr.text + "\n\n\n"



print "Script End!"