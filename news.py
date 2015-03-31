
import log
import argparse
import nyt
import re

def GetSearchData(fileName):
	searchData = []
	f = open(fileName, 'r')
	eventId = 1
	for line in f:
		data = re.match('(.*?)\t(\d{1,2})/(\d{1,2})/(\d{4})(.*)', line)
		if not data:
			continue
		keyWord = data.group(1)
		year = data.group(4)
		month = data.group(2)
		if len(month) == 1:
			month = '0' + month
		day = data.group(3)
		if len(day) == 1:
			day = '0' + day
		searchData.append((eventId, keyWord, year + month + day))
		eventId = eventId +1
	return searchData

# Argument parsing
parser = argparse.ArgumentParser(description='Collect news articles using the keyword from the given data file')
parser.add_argument('-file', 
	type=str,
	default="data.txt",
	help='The data file providing event id, keyword and time period. This file shoud be tab-seperated text file format. The default is \"data.txt\"')
args = parser.parse_args()

log.debug("- Read data file : %s" % args.file)
# Read data file and build the search data table
searchData = GetSearchData(args.file)

# Run!
for event in searchData:
	nyt.run(event[0], event[1], event[2])
	ct.run(event[0])

