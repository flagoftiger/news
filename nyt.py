import pycurl
from StringIO import StringIO
import datetime
import json
import re
import os
from HTMLParser import HTMLParser

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
cookieFileName = "nyt_cookie"

def GetCookie():
	if os.path.isfile(cookieFileName):
		return "already cached"
	cookie = ""
	header = StringIO()
	data = StringIO()
	c = pycurl.Curl()
	c.setopt(c.URL, 'http://www.nytimes.com/')
	c.setopt(c.WRITEHEADER, header)
	c.setopt(c.WRITEDATA, data)
	try:
		c.perform()
	except:
		print "WARNING: curl error"
	c.reset()
	lines = header.getvalue().split()
	# 200 OK
	if lines.count > 1:
		if lines[1] == '200':
			# Find 'Set-Cookie:' in header, the next string should be cookie
			cookieIndex = lines.index('Set-Cookie:')
			# The cookie string might contain path information fllowing ';'
			# Get rid of the path information
			cookie = lines[cookieIndex + 1].split(';')[0]
		else:
			print 'WARNING: HTTP ERROR', lines[1]
	else:
		print 'WARNING: HTTP ERROR'
	header.close()
	data.close()
	# Save cookie to file
	f = open(cookieFileName, 'wb')
	f.write(cookie)
	f.close()
	return cookie

def Search(keyWord, beginDate, period, page):
	searchResult = []
	# Calucate the endDate
	beginDateTime = datetime.date(int(beginDate[0:4]), int(beginDate[4:6]), int(beginDate[6:8]))
	endDateTime = beginDateTime + datetime.timedelta(days=period)
	endDate = "%(y)4s%(m)2s%(d)2s" % {"y": endDateTime.year, "m": endDateTime.month, "d": endDateTime.day}
	endDate = endDate.replace(' ', '0')
	# Construct the search url
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
		print "WARNING: curl error:", keyWord, beginDate, period, page
	c.reset()

	lines = header.getvalue().split()
	# 200 OK
	if lines.count > 1:
		if lines[1] == '200':
			jsonResult = json.loads(data.getvalue())
			docs = jsonResult[u'response'][u'docs']
			if len(docs) == 0:
				return None
			for article in docs:
				if article[u'type_of_material'] == "News":
					date = re.search('(\d{4})-(\d{2})-(\d{2})T.{9}', article[u'pub_date'])
					searchResult.append((article[u'web_url'], date.group(1) + date.group(2) + date.group(3)))
		else:
			print 'WARNING: HTTP ERROR', lines[1]
	else:
		print 'WARNING: HTTP ERROR'

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
	try:
		c.perform()
	except:
		print "WARNING: curl error:", eventId, url
	c.reset()
	lines = header.getvalue().split('\r\n')
	# 200 OK
	if lines.count <= 1:
		print 'WARNING: HTTP ERROR'
		return
	try:
		lines.index('HTTP/1.1 200 OK')
	except:
		print 'WARNING: HTTP ERROR might be missing web page'
		return

	# parsing data and get the body paragraph
	parser = NYTParser()
	parser.feed(data.getvalue().decode('utf-8', 'ignore'))
	paragraphs = parser.GetParagraph()
	title = parser.GetTitle()
	parser.ResetParser()

	if len(paragraphs) == 0:
		print "WARNING: empty page:", eventId, url
		f = open("error.txt", 'w+')
		f.write(url)
		f.write(data.getvalue())
		f.close()
		return
	# open file and write down
	fileName = str(eventId) + '_' + newsProvider + '_' + date + '_' + title + '.txt'
	f = open(str(eventId) + '/' + fileName, 'wb')
	print "- Writing : %s" % fileName
	for paragraph in paragraphs:
		f.write(paragraph.encode('UTF-8', 'ignore'))
	f.close()

def run(eventId, keyWord, beginDate, period=180):
	print "- Run NYT with", eventId, keyWord, beginDate, period
	print "- Getting the cookie from NYT"
	c = pycurl.Curl()
	cookie = GetCookie()
	if cookie == "":
		print("ERROR: Failed to get cookie from NYT")
		c.close()
		return
	print "- Searching with", keyWord, "from" , beginDate, "for", period, "days..."
	articleURLs = []
	page = 0
	while True:
		pageArticleUrls = Search(keyWord, beginDate, period, page)
		print '  page', page
		# If returned None it means there was no result anymore.
		if not pageArticleUrls:
			break
		articleURLs = articleURLs + pageArticleUrls
		page = page + 1
	print "- Found %d articles" % len(articleURLs)
	# Make output folder
	try:
		os.mkdir(str(eventId))
	except:
		pass
	print "- Getting the article bodies and write to files"
	for url in articleURLs:
		print "- Getting article from", url[0]
		WriteArticleBody(eventId, url[0], url[1])
	print "- Finished NYT", eventId, keyWord, beginDate, period
	c.close()

if __name__ == "__main__":
    run(12, 'Microsoft', '20090123')