import log
import pycurl
from StringIO import StringIO
import datetime
import json
import re
import os
from HTMLParser import HTMLParser
import urllib

# Html parser class to subtract article body
class NYTParser(HTMLParser):

	def __init__(self):
		HTMLParser.__init__(self)
		self.nytHeadline = False;
		self.nytText = False;
		self.nytParagraph = False;
		self.title = ""
		self.paragraph = [];

	def handle_starttag(self, tag, attrs):
		if tag == "title":
			self.nytHeadline = True
		if tag == "nyt_text":
			self.nytText = True
		if tag == "p":
			if self.nytText:
				if len(attrs) == 0:
					self.nytParagraph = True
				else:
					if attrs[0][0] == 'itemprop' and attrs[0][1] == 'articleBody':
						self.nytParagraph = True
			else:
				if len(attrs) > 0:
					if attrs[0][0] == 'class' and attrs[0][1].find('story-body-text') != -1:
						self.nytParagraph = True
		if tag == 'div':
			if len(attrs) > 0 and attrs[0][0] == 'class' and attrs[0][1] == 'articleBody':
				self.nytText = True

	def handle_endtag(self, tag):
		if tag == "title":
			self.nytHeadline = False
		if tag == "nyt_text" and self.nytText:
			self.nytText = False
		if tag == "p" and self.nytParagraph:
			self.nytParagraph = False
		if tag == "div"	and self.nytParagraph:
			self.nytParagraph = False

	def handle_data(self, data):
		if self.nytParagraph:
			self.paragraph.append(re.sub('[\n\r]]', '', data))
		else:
			if self.nytHeadline:
				self.title = re.sub('NYTimes\.com', '', data)
				self.title = re.sub('\W', '', self.title)

	def GetTitle(self):
		return self.title

	def GetParagraph(self):
		return self.paragraph

	def ResetParser(self):
		HTMLParser.reset(self)
		self.nytHeadline = False;
		self.nytText = False;
		self.nytParagraph = False;
		self.title = ""
		self.paragraph = [];


# Global vars
# url for the NYT article search api
#FIXME: need to get entire matching results. currently only get 10 result
url = 'http://api.nytimes.com/svc/search/v2/articlesearch.json?q=%(q)s&begin_date=%(bd)s&end_date=%(ed)s&sort=newest&page=%(p)s&api-key=%(ak)s'
apiKey = '96e7d7c2bc5ea0ba08e7ac33015d03ba:1:71635418'
newsProvider = "NYT"
cookieFileName = "./nyt_cookie"

def GetCookie():
	if os.path.isfile(cookieFileName):
		log.info("The cookie file already exsists. If the HTTP error occurred, please delete %s file manually" % cookieFileName)
	cookie = ""
	header = StringIO()
	data = StringIO()
	c = pycurl.Curl()
	c.setopt(c.URL, 'http://www.nytimes.com/')
	c.setopt(c.WRITEHEADER, header)
	c.setopt(c.WRITEDATA, data)
	c.setopt(c.COOKIEJAR, cookieFileName)
	c.setopt(c.COOKIEFILE, cookieFileName)
	try:
		c.perform()
	except:
		log.error("curl error. Please retry later.")
		return False
	c.reset()
	lines = header.getvalue().split()
	# 200 OK
	if lines.count > 1:
		if lines[1] != '200':
			log.error("HTTP ERROR %s" % lines[1])
			return False
	else:
		log.error("HTTP ERROR")
		return False
	header.close()
	data.close()
	log.debug("Succeeded to get the cookie")
	return True

def Search(keyWord, beginDate, period, page):
	searchResult = []
	# Calucate the endDate
	beginDateTime = datetime.date(int(beginDate[0:4]), int(beginDate[4:6]), int(beginDate[6:8]))
	endDateTime = beginDateTime + datetime.timedelta(days=period)
	endDate = "%(y)4s%(m)2s%(d)2s" % {"y": endDateTime.year, "m": endDateTime.month, "d": endDateTime.day}
	endDate = endDate.replace(' ', '0')
	# Construct the search url
	keyWord = urllib.quote(keyWord, '')
	searchUrl = url % {"q": '+'.join(keyWord.split()), "bd": beginDate, "ed": endDate, "p": page, "ak": apiKey}
	header = StringIO()
	data = StringIO()
	c = pycurl.Curl()
	c.setopt(c.URL, searchUrl)
	c.setopt(c.WRITEHEADER, header)
	c.setopt(c.WRITEDATA, data)
	try:
		c.perform()
	except:
		log.error("curl error: %s %s %d page=%d" % (keyWord, beginDate, period, page))
	c.reset()

	lines = header.getvalue().split()
	# 200 OK
	if lines.count > 1:
		if lines[1] == '200':
			try:
				jsonResult = json.loads(data.getvalue())
			except:
				log.warning("json error retry once")
				jsonResult = json.loads(data.getvalue())
			docs = jsonResult[u'response'][u'docs']
			if len(docs) == 0:
				return None
			for article in docs:
				if article[u'type_of_material'] == "News":
					date = re.search('(\d{4})-(\d{2})-(\d{2})T.{9}', article[u'pub_date'])
					searchResult.append((article[u'web_url'], date.group(1) + date.group(2) + date.group(3)))
		else:
			log.error('HTTP ERROR %s' % lines[1])
	else:
		log.error('HTTP ERROR')

	header.close()
	data.close()
	return searchResult

def WriteArticleBody(eventId, url, date):
	# Get the web page using the cookie and subtract the body paragraph with a specific html tag
	# and write to file
	header = StringIO()
	data = StringIO()
	c = pycurl.Curl()
	c.setopt(c.URL, url)
	# Need to set the location option for 303 error
	c.setopt(c.FOLLOWLOCATION, True)
	# Need to set cookie information to avoid forwarding to the login page
	c.setopt(c.COOKIEFILE, cookieFileName)
	c.setopt(c.WRITEHEADER, header)
	c.setopt(c.WRITEDATA, data)
	c.setopt(c.COOKIEJAR, cookieFileName)
	c.setopt(c.COOKIEFILE, cookieFileName)
	try:
		c.perform()
	except:
		log.warning("curl error: %d %s retry once" % (eventId, url))
		c.perform()
	c.reset()
	lines = header.getvalue().split('\r\n')
	# 200 OK
	if lines.count <= 1:
		log.error("HTTP ERROR")
		return
	try:
		lines.index('HTTP/1.1 200 OK')
	except:
		try:
			lines.index('HTTP/1.1 404 Not Found')
			log.info("HTTP 404 ERROR. The link was broken. Just skip this page.")
		except:
			log.error("HTTP ERROR")
			print header.getvalue()
		return

	# parsing data and get the body paragraph
	parser = NYTParser()
	parser.feed(data.getvalue().decode('UTF-8', 'ignore'))
	paragraphs = parser.GetParagraph()
	title = parser.GetTitle()
	parser.ResetParser()

	if len(paragraphs) == 0:
		log.info("empty page: %d, %s" % (eventId, url))
		f = open("error.txt", 'w+')
		f.write(url)
		f.write(data.getvalue())
		f.close()
		return
	# open file and write down
	fileName = str(eventId) + '_' + newsProvider + '_' + date + '_' + title + '.txt'
	f = open(str(eventId) + '/' + fileName, 'wb')
	log.debug("Writing : %s" % fileName)
	for paragraph in paragraphs:
		f.write(paragraph.encode('UTF-8', 'ignore'))
	f.close()

def run(eventId, keyWord, beginDate, period=180):
	log.debug("Run NYT with %d %s %s %d" % (eventId, keyWord, beginDate, period))
	log.debug("Getting the cookie from NYT")
	c = pycurl.Curl()
	if not GetCookie():
		log.error("Failed to get cookie from NYT")
		c.close()
		return
	log.debug("Searching with %s from %s for %d" % (keyWord, beginDate, period))
	articleURLs = []
	page = 0
	while True:
		pageArticleUrls = Search(keyWord, beginDate, period, page)
		log.debug("page %d" % page)
		# If returned None it means there was no result anymore.
		if not pageArticleUrls:
			break
		articleURLs = articleURLs + pageArticleUrls
		page = page + 1
	log.debug("Found %d articles" % len(articleURLs))
	# Make output folder
	try:
		os.mkdir(str(eventId))
	except:
		pass
	log.debug("Getting the article bodies and write to files")
	for url in articleURLs:
		log.debug("Getting article from %s" % url[0])
		WriteArticleBody(eventId, url[0], url[1])
	log.debug("Finished NYT %d %s %s %d" % (eventId, keyWord, beginDate, period))
	c.close()

if __name__ == "__main__":
    run(12, 'Microsoft', '20090123')