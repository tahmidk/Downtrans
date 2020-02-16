# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[wn_downtrans.py]
  Description:	This module downloads and translates series from 
  				ncode.syosetu using custom dictionaries that make
  				the machine translation much more readable
"""

# =========================[ Imports ]==========================
from timeit import default_timer as timer 	# Timer
from collections import OrderedDict			# Ordered Dictionary
from tqdm import tqdm						# Progress bar
from pdb import set_trace					# Python debugger
from urllib.request import Request, urlopen	# Fetch URL Requests
from stat import S_IREAD, S_IRGRP, S_IROTH 	# Changing file permissions

import sys, os, io, shutil			# System operations
import winsound 					# Sounc alarm
import time 						# For sleeping thread between retries

import itertools as it 				# Iteration tool
import argparse as argp 			# Parse input arguments
import multiprocessing as mp 		# Multiprocessing tasks
import subprocess 					# Open file in preferred text editor
import webbrowser					# Open translation HTMLs in browser
import ssl 							# For certificate authentication

# Internal dependencies
import configdata			# Custom config data structure
import htmlparser			# Custom html parsing class

# =========================[ Constants ]=========================
# Maximum number of retries on translate and URL fetching
MAX_TRIES = 5

# Sound alarm constants
ALARM_DUR = 100 	# milliseconds (ms)
ALARM_FREQ = 600 	# hertz (Hz)

# File paths
DICT_PATH = 		os.path.join("../dicts/")
RAW_PATH = 			os.path.join("../raws/")
TRANS_PATH = 		os.path.join("../trans/")
LOG_PATH = 			os.path.join("../logs/")
RESOURCE_PATH = 	os.path.join("../resources/")
CONFIG_FILE_PATH = 	os.path.join("../user_config.json")

# Format of the divider for .dict file
DIV = " --> "

# Global config data container
config_data = None
# Global specialized parser
html_parser = None

#============================================================================
#  Initializer functions
#============================================================================
def initConfig():
	"""-------------------------------------------------------------------
		Function:		[initConfig]
		Description:	Initializes config data using user_config.txt
		Input:			None
		Return:			None
		------------------------------------------------------------------
	"""
	# If config file does not exist, create it and exit
	if not os.path.exists(CONFIG_FILE_PATH):
		print("\n[Error] user_config.json file does not exist. Creating file \
			skeleton...")
		try:
			src_dir = os.path.join(RESOURCE_PATH + "config_skeleton.json")
			dst_dir = CONFIG_FILE_PATH
			shutil.copy(src_dir, dst_dir)
		except Exception:
			print("\n[Error] Error creating user_config.json. Exiting...")
			sys.exit(1)

		print("\nuser_config.json created. Please add some series entries and \
			try again. Exiting...")
		sys.exit(0)

	# Otherwise, read config file and initialize globals
	global config_data
	config_data = configdata.ConfigData(CONFIG_FILE_PATH)

	# Post-config validation 
	if config_data.getNumHosts() == 0:
		print("\n[Error] No hosts detected. Please add at least 1 host in \
			user_config.json under hosts")
		print("Exiting...")
		sys.exit(1)
	if config_data.getNumSeries() == 0:
		print("\n[Error] No series detected. Please add some series in \
			user_config.json under series")
		print("Exiting...")
		sys.exit(1)

def initEssentialPaths():
	"""-------------------------------------------------------------------
		Function:		[initEssentialPaths]
		Description:	Creates certain necessary directories if they don't
						already exist
		Input:			None
		Return:			None
		------------------------------------------------------------------
	"""
	if not os.path.exists(DICT_PATH):
		os.makedirs(DICT_PATH)
	if not os.path.exists(RAW_PATH):
		os.makedirs(RAW_PATH)
	if not os.path.exists(TRANS_PATH):
		os.makedirs(TRANS_PATH)
	if not os.path.exists(LOG_PATH):
		os.makedirs(LOG_PATH)

def initArgParser():
	"""-------------------------------------------------------------------
		Function:		[initArgParser]
		Description:	Initializes the arg parser and runs sanity checks on 
						user provided arguments
		Input:			None
		Return:			The arg parser
		------------------------------------------------------------------
	"""
	# Initialize parser and description
	parser = argp.ArgumentParser(description="Download and run special \
		translation on chapters directly from various host websites")

	# Mode flags are mutually exclusive: Either single or batch downtrans
	mode_flags = parser.add_mutually_exclusive_group(required=True)
	mode_flags.add_argument('-C', '--clean',
		action="store_true",
		help="Clean the /raw and /trans subdirectories"
		)
	mode_flags.add_argument('-B', '--batch',
		action="store_true", 
		help="Downloads and translates a batch of chapters")
	mode_flags.add_argument('-O', '--one',
		action="store_true", 
		help="Downloads and translates one chapter")

	if len(sys.argv) > 1:
		args = sys.argv[1:]
		if args[0] == '-C' or args[0] == '--clean':
			r = handleClean()
			if r == 0:
				print("\n[Success] /raws and /trans cleaned. Exiting...")
			else:
				print(("\n[Complete] Cleaned all but %d files. Exiting..." % r))
			sys.exit(0)

	# Positional arguments
	parser.add_argument('series', 
		help="Which series to download and translate with a dictionary")
	parser.add_argument('start',
		type=int,
		help="The chapter number to start downtrans process at")
	parser.add_argument('end',
		type=int,
		nargs='?',
		help="The chapter number to end downtrans process at")

	# Handle errors or address warnings
	args = parser.parse_args()

	# Series mapping does not exist in config data
	global config_data
	if not config_data.seriesIsValid(args.series):
		parser.error("The series '"+str(args.series)+"' does not exist in the \
			source code mapping")
	# Batch command w/out 'end' chapter argument
	if args.batch and not args.end:
		parser.error("For batch downloads, both a start and end chapter are \
			required")
	# Single commang w/ 'out' chapter argument
	elif args.one and args.end:
		print(("[Warning] Detected flag -O for single download-translate but \
			received both a 'start'\nand 'end' argument. Ignoring argument \
			end=%d...." % args.end))
	# Chapter numbering starts at 1
	if args.start < 1:
		parser.error("Start chapter argument is a minimum of 1 [start=%d]" % 
			args.start)
	# End chapter must be greater than start chapter
	if args.batch and not (args.start < args.end):
		parser.error("End chapter must be greater than start chapter [start=%d,\
		 end=%d]" % (args.start, args.end))

	return parser

def initHtmlParser(host):
	"""-------------------------------------------------------------------
		Function:		[initHtmlParser]
		Description:	Initializes the global html parser using the given
						host name
		Input:
		  [host]		The host associated with a given series
		Return:			0 on success
		------------------------------------------------------------------
	"""
	global html_parser
	global config_data

	if host == "Syosetu":
		html_parser = htmlparser.SyosetuParser()
		return 0
	elif host == "Biquyun":
		html_parser = htmlparser.BiquyunParser()
		return 0
	elif host == "69shu":
		html_parser = htmlparser.Shu69Parser()
		return 0
	
	print("Unrecognized host %s! Make sure this host has an entry in the\
		hosts field of user_config.json" % host)
	sys.exit(1)

def initDict(series):
	"""-------------------------------------------------------------------
		Function:		[initDict]
		Description:	Initializes and returns the dictionary from .dict file 
		Input:
		  [series]		the series to initialize dictionary file (.dict) for
		Return:			Returns a dict() structure with the mappings indicated 
						in dict_file
		------------------------------------------------------------------
	"""
	# Open dict file in read mode
	try:
		dict_name = series.lower() + ".dict"
		dict_file = io.open(os.path.join(DICT_PATH, dict_name), 
			mode='r', 
			encoding='utf8'
		)
	except Exception:
		print("[Error] Error opening dictionary file. Make sure '.dict' exists \
			in the dict/ folder... ")
		sys.exit(1)

	# Parse the mappings into a list
	dictList = []
	for line in dict_file:
		# Skip unformatted/misformatted lines
		if not DIV in line:
			continue

		line = line[:-1]	# Ignore newline '\n' at the end of the line
		dictList.append(line.split(DIV))

	series_dict = OrderedDict(dictList)
	dict_file.close()
	return series_dict

#============================================================================
#  Utility functions
#============================================================================
def handleClean():
	"""-------------------------------------------------------------------
		Function:		[handleClean]
		Description:	Clean the /trans and /raws subdirectories
		Input:			None
		Return:			0 upon success. 1 if function fails to remove at least 
						1 file in either subdirectory
		------------------------------------------------------------------
	"""
	ret = 0

	print(("\nCleaning directory: %s..." % RAW_PATH))
	raw_dir = os.listdir(RAW_PATH)
	for file in raw_dir:
		path = os.path.join(RAW_PATH, file)
		print(("\tremoving [%s]...\t" % path), end='')
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			ret = ret + 1
			continue
		print("Complete")

	print(("\nCleaning directory: %s..." % TRANS_PATH))
	trans_dir = os.listdir(TRANS_PATH)
	for file in trans_dir:
		path = os.path.join(TRANS_PATH, file)
		print(("\tremoving [%s]...\t" % path), end='')
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			ret = ret + 1
			continue
		print("Complete")

	print(("\nCleaning directory: %s..." % LOG_PATH))
	log_dir = os.listdir(LOG_PATH)
	for file in log_dir:
		path = os.path.join(LOG_PATH, file)
		print(("\tremoving [%s]...\t" % path), end='')
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			ret = ret + 1
			continue
		print("Complete")

	return ret

def openBrowser(series, ch):
	"""-------------------------------------------------------------------
		Function:		[openBrowser]
		Description:	Opens a given chapter in select browser
		Input:
		  [series]		The series name
		  [ch]			The chapter to open
		Return:			N/A
		------------------------------------------------------------------
	"""
	global config_data
	if config_data.getPreferredBrowser() is None:
		print("No preferred browser detected. Please open translation files \
			manually or input a path for your preferred browser .exe file in \
			user_config.json")
	else:
		path_trans = TRANS_PATH + "t%s_%d.html" % (series, ch)
		try:
			webbrowser.get('google-chrome').open('file://' + \
				os.path.realpath(path_trans)
			)
		except OSError:
			print("\n[Error] The preferred browser [%s] does not exist. \
				Skipping" % PREFERRED_BROWSER_PATH)
		except Exception:
			print("\n[Error] Cannot open the preferred reader [%s]. \
				Skipping" % PREFERRED_BROWSER_PATH)

#============================================================================
#  Web scraping functions
#============================================================================
def getSeriesURL(series, ch):
	"""-------------------------------------------------------------------
		Function:		[getSeriesURL]
		Description:	Returns the complete url for the series and chapter
		Input:			
		  [series]		The series to build url for
		  [ch]			The chapter to build url for
		Return: 		The full URL of the page containing chapter [ch] of
						[series]
		------------------------------------------------------------------
	"""
	global config_data
	base_url = config_data.getHostUrl(config_data.getSeriesHost(series))
	series_code = config_data.getSeriesCode(series)

	series_url = base_url + series_code + "/" + str(ch) + "/"
	return series_url

def fetchHTML(url, lang):
	"""-------------------------------------------------------------------
		Function:		[fetchHTML]
		Description:	Tries to prompt a response url and return the received
						HTML content as a UTF-8 decoded string
		Input:			
		  [url]			The url to make the request to
		  [lang]		The page's language, determines decoding scheme
		Return: 		The HTML content of the given website address
		------------------------------------------------------------------
	"""
	tries = 0
	while True:
		try:
			headers = { 'User-Agent' : 'Mozilla/5.0' }
			request = Request(url, None, headers)
			response = urlopen(request, context=ssl._create_unverified_context())
			break
		# Some error has occurred
		except Exception as e:
			tries += 1
			print("\n[Error] Could not get response from <%s>... Retrying \
				[tries=%d]" % (url, tries))
			time.sleep(2)
		
		if tries == MAX_TRIES:
			print("\n[Error] Max tries reached. No response from <%s>. Make \
				sure this URL exists" % url)
			return None

	# Read and decode the response according to series language
	source = response.read()
	if lang == "JP":
		data = source.decode('utf8')
	elif lang == "CN":
		data = source.decode('gbk')
	else:
		print("Unrecognized language option: \'%s\'" % lang)
		sys.exit(1)

	return data

#============================================================================
#  Writer functions
#============================================================================
def writeRaw(series, ch, content):
	"""-------------------------------------------------------------------
		Function:		[writeRaw]
		Description:	Write raw to raw file
		Input:
		  [series]	The series to write raw for
		  [ch]		The chapter number to write raw for
		  [content]	The (raw) content to write, a list
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Open raw file in write mode
	try:
		raw_name = "r%s_%d.txt" % (series, ch)
		raw_file = io.open(os.path.join(RAW_PATH, raw_name),
			mode='w', 
			encoding='utf8'
		)
	except Exception:
		print(("[Error] Error opening raw file [%s]" % raw_name))
		print("\nExiting...")
		return 1

	# Write to raw
	for line in content:
		raw_file.write(line)
		raw_file.write('\n')

	# Close raw file
	raw_file.close()
	return 0

def setPrevLink(resource_string, series, ch):
	"""-------------------------------------------------------------------
		Function:		[setPrevLink]
		Description:	Insert anchor to previous chapter html file into 
						given resource string or fake anchor if file DNE
		Input:
		  [resource_string] the string version of the html translation
		  [series]			series name
		  [ch]				current chapter number
		Return:			resource_string with the previous chapter anchor
						incorporated
		------------------------------------------------------------------
	"""
	if ch > 1:
		prev_file_name = "t%s_%d.html" % (series, ch-1)
		prev_file_path = os.path.join(TRANS_PATH, prev_file_name)
		return re.sub(r'PREV_CHAPTER_ANCHOR', prev_file_name, resource_string)

	return re.sub(r'PREV_CHAPTER_ANCHOR', r'#', resource_string)

def setNextLink(resource_string, series, ch):
	"""-------------------------------------------------------------------
		Function:		[setNextLink]
		Description:	Insert anchor to next chapter html file into 
						given resource string or fake anchor if file DNE
		Input:
		  [resource_string] the string version of the html translation
		  [series]			series name
		  [ch]				current chapter number
		Return:			resource_string with the next chapter anchor
						incorporated
		------------------------------------------------------------------
	"""
	next_file_name = "t%s_%d.html" % (series, ch+1)
	next_file_path = os.path.join(TRANS_PATH, next_file_name)
	return re.sub(r'NEXT_CHAPTER_ANCHOR', next_file_name, resource_string)

def setPageTitle(resource_string, pg_title):
	"""-------------------------------------------------------------------
		Function:		[setPageTitle]
		Description:	Inserts a page title as an html tag into the 
						given resource string
		Input:
		  [resource_string] the string version of the html translation
		  [pg_title]		the page title string
		Return:			resource_string with the chapter title incorporated
		------------------------------------------------------------------
	"""
	return re.sub(r'<!--PAGE_TITLE-->', pg_title, resource_string)

def setChapterTitle(resource_string, ch_title):
	"""-------------------------------------------------------------------
		Function:		[setChapterTitle]
		Description:	Inserts a chapter title as an html header into the 
						given resource string
		Input:
		  [resource_string] the string version of the html translation
		  [ch_title]		the chapter title string
		Return:			resource_string with the chapter title incorporated
		------------------------------------------------------------------
	"""
	return re.sub(r'<!--CHAPTER_TITLE-->', ch_title, resource_string)

def insertLine(resource_string, line):
	"""-------------------------------------------------------------------
		Function:		[insertLine]
		Description:	Inserts a line as an html paragraph into the given 
						resource string
		Input:
		  [resource_string] the string version of the html translation
		  [line]			the line to add an html element for
		Return:			resource_string with the line incorporated
		------------------------------------------------------------------
	"""
	line_html = "<p>%s</p>\n<!--END_OF_BODY-->" % line
	return re.sub(r'<!--END_OF_BODY-->', line_html, resource_string)

def writeTrans(series, ch, title, series_dict, log_file):
	"""-------------------------------------------------------------------
		Function:		[writeTrans]
		Description:	Write translations to trans file
		Input:
		  [series]		The series to write translation for
		  [ch]			The chapter number to write translation for
		  [title]		The title string of this chapter
		  [series_dict]	The dict map for this series
		  [log_file]	The associated log file for this translation
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Initialize trans_file
	try:
		trans_name = "t%s_%d.html" % (series, ch)
		trans_file = io.open(os.path.join(TRANS_PATH, trans_name), 
			mode='w', 
			encoding='utf8'
		)
	except Exception:
		print(("[Error] Error opening translation file [%s]" % trans_name))
		print("\nExiting...")
		return 1

	# Open raw_file
	try:
		raw_name = "r%s_%d.txt" % (series, ch)
		raw_file = io.open(os.path.join(RAW_PATH, raw_name), 
			mode='r', 
			encoding='utf8'
		)
	except Exception:
		print(("[Error] Error opening raw file [%s]" % raw_name))
		print("\nExiting...")
		return 1

	# Open and read reference html
	try:
		resource_file = io.open(os.path.join(RESOURCE_PATH), 
			mode='r', 
			encoding='utf8'
		)
		resource_string = resource_file.read()
		resource_string = setPageTitle(resource_string, "%s | %d" % (series, ch))
		resource_string = setChapterTitle(resource_string, title)
		resource_string = setPrevLink(resource_string, series, ch)
		resource_string = setNextLink(resource_string, series, ch)
	except Exception:
		print(("[Error] Error opening or using resource file [%s]" % raw_name))
		print("\nExiting...")
		return 1		

	# Count number of lines in raw source file
	num_lines = 0
	raw_list = []
	for line in raw_file: 
		num_lines += 1
		raw_list.append(line)

	#import pdb; pdb.set_trace()
	ret = 0
	line_num = 0
	placeholder_id = 1
	for line in tqdm(raw_list, total=num_lines):
		line_num += 1

		# Skip blank lines
		if line == '\n':
			resource_string = insertLine(resource_string, '\n')
			continue

		# Check raw text against dictionary and replace matches
		log_file.write("\n[L%d] Processing non-blank line..." % line_num)
		line = line + '\n'
		prepped = line
		for entry in series_dict:
			if entry in prepped:
				log_file.write("\n\tDetected token %s in line. Replacing \
					with %s" % (entry, series_dict[entry]))
				placeholder = "<span class=\"placeholder\" id=%d>placeholder\
					</span>" % placeholder_id
				new_entry = "<span class=\"notranslate\" id=w%d>%s</span>" % 
					(placeholder_id, series_dict[entry])
				prepped = prepped.replace(entry, "%s%s" % 
					(new_entry, placeholder))
				
				log_file.write("\n\tPrepped=%s" % prepped)
				placeholder_id += 1

		# Add line to the resource string
		resource_string = insertLine(resource_string, prepped)

	# Write to trans file
	trans_file.write(resource_string)

	# Close all files file
	print(("Downtrans [t%s_%s.html] complete!" % (series, ch)))
	raw_file.close()
	trans_file.close()
	return ret

# =========================[ Script ]=========================
def batch_procedure(series, ch_queue):
	"""-------------------------------------------------------------------
		Function:		[batch_procedure]
		Description:	Does the default procedure on each chapter in the list
						of [chapters]
		Input:
		  [series]	 The series for which to downtrans chapter
		  [ch_queue] The list of chapter numbers to downtrans
		Return:			N/A
		------------------------------------------------------------------
	"""
	print(("Downtransing %s chapters: %s" % (series, str(ch_queue))))
	print("This may take a minute or two...")

	# Multiprocess queue of chapters requested
	pool = mp.Pool(processes=mp.cpu_count())
	args = [(series, ch) for ch in ch_queue]

	results = pool.imap_unordered(_default_procedure, args)
	pool.close()
	pool.join()

	print("\nError Report (Consider redownloading erroneous chapters w/ -O flag)")
	ret_codes = list(results)
	for i in range(0, len(ret_codes)):
		if ret_codes[i] == 0:
			print(("\tChapter %s: SUCCESS" % ch_queue[i]))
		else:
			print(("\tChapter %s: FAILURE" % ch_queue[i]))

def _default_procedure(args):
	""" Simple wrapper method for pooling default_procedure """
	return default_procedure(*args)

def default_procedure(series, ch):
	"""-------------------------------------------------------------------
		Function:		[default_procedure]
		Description:	Downloads and saves a raw for chapter [ch] of series 
						[series] and translates chapter with the dict 
						associated with [series]
		Input:
		  [series]	The series for which to downtrans chapter
		  [ch]		The integer indicating which chapter to downtrans
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Ret code: 0 - success, non-0 - failure
	ret = 0

	# Fetch the html source code
	url = getSeriesURL(series, ch)
	html = fetchHTML(url)
	if html == None:
		return 1

	# Parse out relevant content from the website source code
	global html_parser
	title = html_parser.parseTitle(html)
	content = html_parser.parseContent(html)
	ret += writeRaw(series, ch, content)

	# Initialize series dictionary
	series_dict = initDict(series)

	# Try to open a log file to log translation details
	try:
		log_name ="l%s_%d.log" % (series, ch)
		log_file = io.open(os.path.join(LOG_PATH, log_name), mode='w', encoding='utf8')
	except Exception:
		print("[Error] Error opening log file... ")
		return 1

	# Write translation as HTML
	ret += writeTrans(series, ch, title, series_dict, log_file)
	log_file.close()

	return ret


def main():
	start = timer()
	#Initialize config data from user_config.json
	initConfig()

	# Fetch arguments from parser
	parser = initArgParser()
	args = parser.parse_args()
	# Initialize arguments
	mode_batch = args.batch
	mode_single = args.one
	series = args.series
	ch_start = args.start
	ch_end = args.end

	# Create subdirectories if they don't already exist
	initEssentialPaths()
	# Initialize the HTML parser corresponding to the host of this series
	initHtmlParser(config_data.getSeriesHost(series))

	# Different execution paths depending on mode
	if mode_batch:
		chapters = list(range(ch_start, ch_end+1))
		batch_procedure(series, chapters)
		openBrowser(series, ch_start)
	elif mode_single:
		err_code = default_procedure(series, ch_start)
		if err_code != 0:
			print("[Error] Could not download or translate. Exiting")
			sys.exit(1)
		openBrowser(series, ch_start)
	else:
		print("[Error] Unexpected mode")
		sys.exit(1)

	# Print completion statistics
	print(("\n[Complete] Check output files in %s" % TRANS_PATH))
	elapsed = timer() - start
	if elapsed > 60:
		elapsed = elapsed / 60
		print(("  Elapsed Time: %.2f min" % elapsed))
	else:
		print(("  Elapsed Time: %.2f sec" % elapsed))

	winsound.Beep(ALARM_FREQ, ALARM_DUR)
	return 0

if __name__ == '__main__':
	# Check python version. Only run this script w/ Python 3
	if not sys.version_info[0] == 3:
		print("[Error] Must run this script w/ Python 3.X.X")
	main()

