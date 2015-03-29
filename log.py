import logging
import datetime

def debug(message):
	log.debug(message)

def info(message):
	log.info(message)

def warning(message):
	log.warning(message)

def error(message):
	log.error(message)


time = datetime.datetime.now().timetuple()
logFileName = "%4s%2s%2s_%2s%2s%2s.log" % (time[0], time[1], time[2], time[3], time[4], time[5])
logFileName = logFileName.replace(' ', '0')
print logFileName

# log setting
log = logging.getLogger('news_logger')
log.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler(logFileName)
fh.setLevel(logging.DEBUG)
# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s %(levelname)s\t%(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
log.addHandler(fh)
log.addHandler(ch)

