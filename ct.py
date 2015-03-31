# For CT the search result file will be provided
# The format of the input file should be CT_{event number}_{page number}.txt

import log
import os
import re
import calendar

inputFolderName = 'input'
newsProvider = 'CT'

def WriteArticleBody(eventId, title, date, body):
	fileName = str(eventId) + '_' + newsProvider + '_' + date + '_' + title + '.txt'
	f = open(str(eventId) + '/' + fileName, 'wb')
	log.debug("Writing : %s" % fileName)
	f.write(body)
	f.close

def Process(eventId, fileName):
	log.debug("Processing %s..." % fileName)
	f = open(fileName, 'r')

	isArticle = False
	title = ''
	body = ''
	date = ''
	while(True):
		line = f.readline()
		# eof
		if line == '':
			if isArticle:
				WriteArticleBody(eventId, title, date, body)
			break
		number = re.search('Document (\d{1,3}) of (\d{1,3})', line)
		if not number:
			if isArticle:
				paragraph = re.search('(.*?): (.*)', line)
				if not paragraph:
					if isArticleBody:
						body = body + line + '\r\n'
					continue
				# End of the body
				if isArticleBody:
					isArticleBody = False
				if paragraph.group(1) == 'Full text':
					isArticleBody = True
					body = paragraph.group(2)
				if paragraph.group(1) == 'Title':
					title = re.sub(' ', '_', paragraph.group(2))
					title = re.sub('\W', '', title)
					title = re.sub('_', '-', title)
				if paragraph.group(1) == 'Publication date':
					search = re.search('Publication date: ([a-zA-Z]+) (\d{1,2}), (\d{4})', line)
					if not search:
						log.error("Invalid date format in\n %s" % atricle)
						return
					year = search.group(3)
					month = str(list(calendar.month_abbr).index(search.group(1)))
					if len(month) == 1:
						month = '0' + month
					day = search.group(2)
					if len(day) == 1:
						day = '0' + day
					date = year + month + day
			continue

		# End of an article
		if isArticle:
			WriteArticleBody(eventId, title, date, body)
		# Start a new article
		log.debug("%s / %s" % (number.group(1), number.group(2)))
		isArticle = True
		isArticleBody = False
		body = ''

	f.close
	log.debug("Finished %s..." % fileName)


def run(eventId):
	log.debug("Run CT with %d" % eventId)
	# Check the input folder and files
	if not os.path.isdir(inputFolderName):
		log.error("Missing input folder: %s" % inputFolderName)
		return
	eventInputFolderName = inputFolderName + '/' + str(eventId)
	if not os.path.isdir(eventInputFolderName):
		log.error("Missing input folder for current event: %s" % eventInputFolderName)
		return
	inputFiles = [ f for f in os.listdir(eventInputFolderName) if os.path.isfile(os.path.join(eventInputFolderName,f)) ]
	if len(inputFiles) == 0:
		log.error("Missing input file for current event: %d" % eventId)
		return

	# Make output folder
	try:
		os.mkdir(str(eventId))
	except:
		pass

	# Process each file
	for f in inputFiles:
		Process(eventId, inputFolderName + '/' + str(eventId) + '/' + f)

	log.debug("Finished CT %d" % eventId)

if __name__ == "__main__":
    run(12)
