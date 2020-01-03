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

import sys, os, io 					# System operations
import winsound 					# Sounc alarm
import time 						# For sleeping thread between retries
import re 							# Regex for parsing HTML

import itertools as it 				# Iteration tool
import argparse as argp 			# Parse input arguments
import multiprocessing as mp 		# Multiprocessing tasks
import subprocess 					# Open file in preferred text editor
import webbrowser					# Open translation HTMLs in browser
import ssl 							# For certificate authentication

# =======================[ WN Constants ]========================
syosetu_url = "https://ncode.syosetu.com/"

# Read chapter content only? Or include author comments in translation too?
content_only = False
# Important globals initialized from user_config.txt
series_map = {}
PREFERRED_BROWSER_PATH = ""



# =========================[ Constants ]=========================
# Maximum number of retries on translate and URL fetching
MAX_TRIES = 5

# Sound alarm constants
ALARM_DUR = 100 	# milliseconds (ms)
ALARM_FREQ = 600 	# hertz (Hz)

# File paths
DICT_PATH = "./dicts/"
RAW_PATH = "./raws/"
TRANS_PATH = "./trans/"
LOG_PATH = "./logs/"
RESOURCE_PATH = "./resources/skeleton.html"

# Format of the divider for .dict file
DIV = " --> "



# =========================[ Functions ]=========================
def initConfig(print_config):
	"""-------------------------------------------------------------------
		Function:		[initConfig]
		Description:	Initializes some important globals using user_config.txt
		Input:			
		  [print_config]Flag to print config statements or not
		Return:			None
		------------------------------------------------------------------
	"""
	# If config file does not exist, create it and exit
	if not os.path.exists("./user_config.txt"):
		print("\n[Error] user_config file does not exist. Creating file skeleton...")
		try:
			config_file = io.open(os.path.join("./user_config.txt"), mode='w', encoding='utf8')
			config_file.write(u"PREFERRED_BROWSER_PATH: path/to/browser.exe\n\n")
			config_file.write(u"SERIES CODE\n")
		except Exception:
			print("\n[Error] Error creating user_config.txt. Exiting...")
			sys.exit(4)

		print("\nuser_config.txt created. Please add some series/code pairs and try again. Exiting...")
		config_file.close()
		sys.exit(0)

	# Otherwise, read config file and initialize globals
	global series_map
	try:
		config_file = io.open(os.path.join("./user_config.txt"), mode='r', encoding='utf8')
		for line in config_file:
			line = line.split(" ", 1)
			if len(line) == 2:
				if line[0] == u"SERIES" and line[1] == u"CODE\n":
					continue
				elif line[0] == "PREFERRED_BROWSER_PATH:":
					global PREFERRED_BROWSER_PATH
					PREFERRED_BROWSER_PATH = line[1][:-1] if line[1][-1] == u'\n' else line[1]
					if print_config:
						print("\nPreferred Reader: \'%s\'" % PREFERRED_BROWSER_PATH)
				else:
					series = line[0]
					code = line[1][:-1] if line[1][-1] == u'\n' else line[1]
					series_map[series] = code
					if print_config:
						print("Series: \'%s\' (Code=%s)" % (series, code))

		if print_config:
			print("\nConfig success. Check that the above information is correct...\n")
		config_file.close()
	except Exception:
		print("\n[Error] Error creating user_config.txt. Exiting...")
		sys.exit(4)

	if len(series_map) == 0:
		print("\n[Error] No series/code pairs detected. Please add some series/code \
			pairs (single space seperated) in user_config.txt under \'SERIES CODE\'")
		print("Exiting...")
		sys.exit(5)


def initParser():
	"""-------------------------------------------------------------------
		Function:		[initParser]
		Description:	Initializes the parser and runs sanity checks on 
						parsed user arguments
		Input:			None
		Return:			The parser
		------------------------------------------------------------------
	"""
	# Initialize parser and description
	parser = argp.ArgumentParser(description="Download and run special translation on chapters directly from ncode.syosetu.com")

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

	# Series mapping does not exist in series_map dictionary
	global series_map
	if not args.series in series_map:
		parser.error("The series '"+str(args.series)+"' does not exist in the source code mapping")
	# Batch command w/out 'end' chapter argument
	if args.batch and not args.end:
		parser.error("For batch downloads, both a start and end chapter are required")
	# Single commang w/ 'out' chapter argument
	elif args.one and args.end:
		print(("[Warning] Detected flag -O for single download-translate but received both a 'start'\nand 'end' argument. Ignoring argument end=%d...." % args.end))
	# Chapter numbering starts at 1
	if args.start < 1:
		parser.error("Start chapter argument is a minimum of 1 [start=%d]" % args.start)
	# End chapter must be greater than start chapter
	if args.batch and not (args.start < args.end):
		parser.error("End chapter must be greater than start chapter [start=%d, end=%d]" % (args.start, args.end))

	return parser

def handleClean():
	"""-------------------------------------------------------------------
		Function:		[handleClean]
		Description:	Clean the /trans and /raws subdirectories
		Input:			None
		Return:			0 upon success. 1 if function fails to remove at least 
						1 file in either subdirectory
		------------------------------------------------------------------
	"""
	retcode = 0

	print(("\nCleaning directory: %s..." % RAW_PATH))
	raw_dir = os.listdir(RAW_PATH)
	for file in raw_dir:
		path = os.path.join(RAW_PATH, file)
		print(("\tremoving [%s]...\t" % path), end='')
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			retcode = retcode + 1
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
			retcode = retcode + 1
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
			retcode = retcode + 1
			continue
		print("Complete")

	return retcode

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
		dict_file = io.open(os.path.join(DICT_PATH, dict_name), mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening dictionary file. Make sure '.dict' exists in the dict/ folder... ")
		print("Proceeding without special translations")
		return ({}, {})

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

def getSeriesURL(series, ch):
	"""-------------------------------------------------------------------
		Function:		[getSeriesURL]
		Description:	Returns the complete url for the series and chapter
		Input:			
		  [series]		The series to build url off of
		  [ch]			The chapter to build url off of
		Return: 		The full URL of the page containing chapter [ch] of
						[series]
		------------------------------------------------------------------
	"""
	global series_map
	return syosetu_url + series_map[series] + "/" + str(ch) + "/"

def fetchHTML(url):
	"""-------------------------------------------------------------------
		Function:		[fetchHTML]
		Description:	Tries to prompt a response url and return the received
						HTML content as a UTF-8 decoded string
		Input:			
		  [url]			The url to make the request to
		Return: 		The HTML content of the given website address
		------------------------------------------------------------------
	"""
	# Request NCode page
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
			print("\n[Error] Could not get response from <%s>... Retrying [tries=%d]" % (url, tries))
			time.sleep(2)
		
		if tries == MAX_TRIES:
			print("\n[Error] Max tries reached. No response from <%s>. Make sure this URL exists" % url)
			return None


	source = response.read()
	data = source.decode('utf8')
	return data

def parseTitle(html):
	"""-------------------------------------------------------------------
		Function:		[parseTitle]
		Description:	Parses the title from the html source code
		Input:
		  [html]	The HTML source code in string form		
		Return:			The string representing the chapter title
		-------------------------------------------------------------------
	"""
	title = re.findall(r'<p class="novel_subtitle">(.*?)</p>', html)
	return title[0]

def parseContent(html):
	"""-------------------------------------------------------------------
		Function:		[parseContent]
		Description:	Parses the chapter content from the html source code
		Input:
		  [html]	The HTML source code in string form		
		Return:			A list constisting of each line of content from the 
						chapter
		-------------------------------------------------------------------
	"""
	content = []

	# Parse lines and make them readable before adding them to content
	lines = re.findall(r'<p id="L(.*?)">(.*?)</p>', html)
	lines = [l[1] for l in lines]
	for line in lines:
		# Turn break tags into new lines
		if line == '<br />':
			content.append('\n')
		else:
			# Filter out <ruby> tags that are commonly found in line
			if "<ruby>" in line:
				line = re.sub(r'<ruby>(.*?)<rb>(.*?)</rb>(.*?)</ruby>', 
					r'\2', line)
			content.append(line)
		content.append('\n')

	#import pdb; pdb.set_trace()
	return content


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
		raw_file = io.open(os.path.join(RAW_PATH, raw_name), mode='w', encoding='utf8')
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
		trans_file = io.open(os.path.join(TRANS_PATH, trans_name), mode='w', encoding='utf8')
	except Exception:
		print(("[Error] Error opening translation file [%s]" % trans_name))
		print("\nExiting...")
		return 1

	# Open raw_file
	try:
		raw_name = "r%s_%d.txt" % (series, ch)
		raw_file = io.open(os.path.join(RAW_PATH, raw_name), mode='r', encoding='utf8')
	except Exception:
		print(("[Error] Error opening raw file [%s]" % raw_name))
		print("\nExiting...")
		return 1

	# Open and read reference html
	try:
		resource_file = io.open(os.path.join(RESOURCE_PATH), mode='r', encoding='utf8')
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
				log_file.write("\n\tDetected token %s in line. Replacing with %s" % (entry, series_dict[entry]))
				placeholder = "<span class=\"placeholder\" id=%d>placeholder</span>" % placeholder_id
				new_entry = "<span class=\"notranslate\" id=w%d>%s</span>" % (placeholder_id, series_dict[entry])
				prepped = prepped.replace(entry, "%s%s" % (new_entry, placeholder))
				
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
	path_trans = TRANS_PATH + "t%s_%d.html" % (series, ch)
	if len(PREFERRED_BROWSER_PATH) == 0:
		print("No preferred browser detected. Please open translation files manually\
			or input a path for your preferred browser .exe file in user_config.txt")
	else:
		try:
			webbrowser.open('file://' + os.path.realpath(path_trans))
		except OSError:
			print("\n[Error] The preferred browser [%s] does not exist. Skipping" % PREFERRED_BROWSER_PATH)
		except Exception:
			print("\n[Error] Cannot open the preferred reader [%s]. Skipping" % PREFERRED_BROWSER_PATH)

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
	initConfig(False)

	# Fetch the html source code
	url = getSeriesURL(series, ch)
	html = fetchHTML(url)
	if html == None:
		return 1

	# Parse out relevant content from the website source code
	title = parseTitle(html)
	content = parseContent(html)
	ret += writeRaw(series, ch, content)

	# Translate and write trans_file
	series_dict = initDict(series)
	try:
		# Open log file in write mode
		log_name ="l%s_%d.log" % (series, ch)
		log_file = io.open(os.path.join(LOG_PATH, log_name), mode='w', encoding='utf8')
	except Exception:
		print("[Error] Error opening log file... ")
		return -1
	ret += writeTrans(series, ch, title, series_dict, log_file)
	log_file.close()

	return ret


def main():
	start = timer()
	initConfig(True)

	# Fetch arguments from parser
	parser = initParser()
	args = parser.parse_args()
	# Initialize arguments
	mode_batch = args.batch
	mode_single = args.one
	series = args.series
	ch_start = args.start
	ch_end = args.end

	# Create subdirectories if they don't already exist
	if not os.path.exists(DICT_PATH):
		os.makedirs(DICT_PATH)
	if not os.path.exists(RAW_PATH):
		os.makedirs(RAW_PATH)
	if not os.path.exists(TRANS_PATH):
		os.makedirs(TRANS_PATH)
	if not os.path.exists(LOG_PATH):
		os.makedirs(LOG_PATH)

	# Different execution paths depending on mode
	if mode_batch:
		chapters = list(range(ch_start, ch_end+1))
		batch_procedure(series, chapters)
		openBrowser(series, ch_start)
	elif mode_single:
		err_code = default_procedure(series, ch_start)
		if err_code != 0:
			print("[Error] Could not download or translate. Exiting")
			sys.exit(5)
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
	# Check python version. Only run this script w/ Python 2
	if not sys.version_info[0] == 3:
		print("[Error] Please run this with Python 3 only")
	main()

