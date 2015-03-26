import pycurl
from StringIO import StringIO
import datetime
import json
import re
import os
from HTMLParser import HTMLParser

class ParserType1(HTMLParser):

	nytText = False;
	nytParagraph = False;

	def handle_starttag(self, tag, attrs):
		if tag == "nyt_text":
			self.nytText = True
		if self.nytText and tag == "p" and len(attrs) == 0:
			self.nytParagraph = True

	def handle_endtag(self, tag):
		if tag == "NYT_TEXT" and self.nytText:
			self.nytText = False
		if tag == "p" and self.nytParagraph:
			self.nytParagraph = False

	def handle_data(self, data):
		if self.nytParagraph:
			print data 


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
		print "ERROR: curl error"
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
			print 'ERROR: HTTP ERROR', lines[1]
	else:
		print 'ERROR: HTTP ERROR'
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
		print "ERROR: curl error:", keyWord, beginDate, period, page
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
				print article[u'type_of_material'], article[u'web_url']
				if article[u'type_of_material'] == "News":
					searchResult.append(article[u'web_url'])
		else:
			print 'ERROR: HTTP ERROR', lines[1]
	else:
		print 'ERROR: HTTP ERROR'

	header.close()
	data.close()
	return searchResult

def WriteArticleBody(eventId, url):
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
		print "ERROR: curl error:", eventId, url
	c.reset()	
	lines = header.getvalue().split('\r\n')
	# 200 OK
	if lines.count <= 1:
		print 'ERROR: HTTP ERROR'
		return
	try:
		lines.index('HTTP/1.1 200 OK')
	except:
		print 'ERROR: HTTP ERROR might be missing web page'
		return

	parser = ParserType1()
	parser.feed(data.getvalue())
	return
	#root = ET.fromstring(data.getvalue())
	#print root
	#return


	# parsing data and get the body paragraph
	finalParagraphs = []
	# Find <p> tag block
	paragraphs = re.findall('<p class=\"story-body-text.*?\">(.*?)</p>', data.getvalue())
	#paragraphs = re.findall('.*?<p.*?>(.*?)</p>.*?', data.getvalue())
	if len(paragraphs) == 0:
		paragraphs = re.findall('<NYT_TEXT(.*?)</NYT_TEXT>', data.getvalue())
	if len(paragraphs) == 0:
		print "WARNING: empty page:", eventId, url
		f = open("error.txt", 'w+')
		f.write(url)
		f.write(data.getvalue())
		f.close()
		return
	# open file and write down
	names = re.search('.*?\/(\d{4})\/(\d{2})\/(\d{2}).*?\/(.*?).html', url)
	if not names:
		print "- Skipped a non-text article"
		return
	fileName = str(eventId) + '_' + newsProvider + '_' + ''.join(names.group(1, 2, 3)) + '_' + names.group(4) + '.txt'
	f = open(str(eventId) + '/' + fileName, 'w')
	print "- Writing : %s" % fileName
	# Remove the other tags such as <a>
	for paragraph in paragraphs:
		f.write(re.sub('<.*?>', '', paragraph))
		f.write('\r\n')
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
		print "- Getting article from", url
		WriteArticleBody(eventId, url)
	print "- Finished NYT", eventId, keyWord, beginDate, period
	c.close()

if __name__ == "__main__":
    run(1, 'GM', '20090601')