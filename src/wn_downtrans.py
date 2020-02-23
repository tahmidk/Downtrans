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
import multiprocessing as mp 		# General mp utilities
import time 						# For sleeping thread between retries

import argparse as argp 			# Parse input arguments
import webbrowser					# Open translation HTMLs in browser
import platform						# Used to determine Operating System
import ssl 							# For certificate authentication

# Internal dependencies
import configdata			# Custom config data structure
import htmlparser			# Custom html parsing class
import htmlwriter			# Custom html writing class

# =========================[ Constants ]=========================
# Maximum number of retries on translate and URL fetching
MAX_TRIES = 5

# File paths
DICT_PATH = 		os.path.join("../dicts/")
RAW_PATH = 			os.path.join("../raws/")
TRANS_PATH = 		os.path.join("../trans/")
TABLES_PATH = 		os.path.join("../tables/")
LOG_PATH = 			os.path.join("../logs/")
RESOURCE_PATH = 	os.path.join("../resources/")
CONFIG_FILE_PATH = 	os.path.join("../user_config.json")

# Format of the divider for .dict file
DIV = r' --> '

# =========================[  Globals  ]=========================
config_data = None   # Global config data container initialized by initConfig
html_parser = None 	 # Global specialized parser initialized by initHtmlParser
series_dict = None   # Global series-specific dict initialized by initDict
page_table  = None 	 # Global series-specific page table init by initPageTable

# Simple package class to share globals w/ child processes
class GlobalsPackage:
	def packGlobal(self, var_name):
		exec("setattr(self, \'%s\', %s)" % (var_name, var_name))


#============================================================================
#  Initializer functions
#============================================================================
def initConfig():
	"""-------------------------------------------------------------------
		Function:		[initConfig]
		Description:	Initializes config data using user_config.txt
		Input:			None
		Return:			None, initializes a global config_data
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
	if not os.path.exists(DICT_PATH):	os.makedirs(DICT_PATH)
	if not os.path.exists(RAW_PATH):	os.makedirs(RAW_PATH)
	if not os.path.exists(TRANS_PATH):	os.makedirs(TRANS_PATH)
	if not os.path.exists(TABLES_PATH):	os.makedirs(TABLES_PATH)
	if not os.path.exists(LOG_PATH):	os.makedirs(LOG_PATH)

def initArgParser():
	"""-------------------------------------------------------------------
		Function:		[initArgParser]
		Description:	Initializes the arg parser and runs sanity checks on 
						user provided arguments
		Input:			None
		Return:			The arg parser
		PRECONDITION:	initConfig() has been invoked before this call
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
		Return:			None, initializes a global html_parser
		PRECONDITION:	initConfig() has been invoked before this call
		------------------------------------------------------------------
	"""
	global html_parser
	global config_data

	if host == "Syosetu":
		html_parser = htmlparser.SyosetuParser()
		return
	elif host == "Biquyun":
		html_parser = htmlparser.BiquyunParser()
		return
	elif host == "69shu":
		html_parser = htmlparser.Shu69Parser()
		return
	
	print("Unrecognized host %s! Make sure this host has an entry in the\
		hosts field of user_config.json" % host)
	sys.exit(1)

def initDict(series):
	"""-------------------------------------------------------------------
		Function:		[initDict]
		Description:	Initializes the global series dictionary 
		Input:
		  [series]		The series to initialize dictionary file (.dict) for
		Return:			None, initializes a global series_dict
		------------------------------------------------------------------
	"""
	global series_dict
	dict_name = series.lower() + ".dict"
	dict_path = os.path.join(DICT_PATH, dict_name)

	if not os.path.exists(dict_path) or os.path.getsize(dict_path) == 0:
		print("No dictionary exists for this series... Creating new dictionary")
		try:
			dict_file = io.open(dict_path, mode='w', encoding='utf8')
			dict_file.write("// NCode Link: %s\n" % getSeriesUrl(series))
			dict_file.write("\n// Example comment (starts w/ \'//\''). \
				Example entry below\n")
			dict_file.write(u'ナルト --> Naruto\n')
			dict_file.write("\n// END OF FILE")
			dict_file.close()
			series_dict = {}
		except Exception:
			print("[Error] Error creating or modifying dict file [%s]" % 
				dict_name)
		return

	# Open dict file in read mode
	try:
		dict_file = io.open(dict_path, mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening dictionary file [%s]" % dict_name)
		sys.exit(1)

	# Parse the mappings into a list
	dictList = []
	for line in dict_file:
		# Skip comment lines and unformatted/misformatted lines
		line = line.lstrip()
		if line[0:2] == "//" or DIV not in line:
			continue

		line = line[:-1]	# Ignore newline '\n' at the end of the line
		dictList.append(line.split(DIV))

	# Initialize the global
	series_dict = OrderedDict(dictList)
	dict_file.close()

def initPageTable(series):
	"""-------------------------------------------------------------------
		Function:		[initPageTable]
		Description:	Initializes the page table global for given series
		Input:			
		  [series]		The series to build the page table for
		Return: 		None, initializes a global page_table
		PRECONDITION:	initHtmlParser() has been invoked before this call
		------------------------------------------------------------------
	"""
	global page_table
	global html_parser
	global config_dat

	table_name = "%s.table" % series.lower()
	series_table = os.path.join(TABLES_PATH, table_name)
	
	# If table is marked as not needed for this parser, skip this function
	if not html_parser.needsPageTable():
		return
	# If .table DNE for this series, parse it from web and write one
	elif not os.path.exists(series_table) or os.path.getsize(series_table) == 0:
		set_trace()
		print("No table file exists for this series... Creating a new table")
		series_index_url = getSeriesUrl(series)
		series_index_html = fetchHTML(series_index_url, config_data.getSeriesLang(series))
		page_table = html_parser.parsePageTableFromWeb(series_index_html)

		# Save to .table file
		try:
			table_file = io.open(series_table, mode='w', encoding='utf8')
			for entry in page_table:
				table_file.write(entry + u'\n')
			table_file.close()
		except Exception:
			print("[Error] Error creating or modifying table file [%s]" % 
				table_name)

		# Mark file as readonly
		os.chmod(series_table, S_IREAD|S_IRGRP|S_IROTH)
	# If .table already exists for this series, just read that in
	else:
		try:
			table_file = io.open(series_table, mode='r', encoding='utf8')
			page_table = []
			for line in table_file:
				if line != u'\n':	page_table.append(line[:-1])
		except Exception:
			print("[Error] Error reading existing series table file [%s]" % 
				table_name)

#============================================================================
#  General utility functions
#============================================================================
def handleClean():
	"""-------------------------------------------------------------------
		Function:		[handleClean]
		Description:	Clean the /trans and /raws subdirectories
		Input:			None
		Return:			0 upon success. 1 if function fails to remove at least 
						one file in either subdirectory
		------------------------------------------------------------------
	"""
	ret = 0

	# Clean up raw/ directory
	print(("\nCleaning directory: %s..." % RAW_PATH))
	raw_dir = os.listdir(RAW_PATH)
	for file in raw_dir:
		path = os.path.join(RAW_PATH, file)
		print(("  removing %-30s:\t" % path), end='')
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			ret = ret + 1
			continue
		print("Complete")

	# Clean up trans/ directory
	print(("\nCleaning directory: %s..." % TRANS_PATH))
	trans_dir = os.listdir(TRANS_PATH)
	for file in trans_dir:
		path = os.path.join(TRANS_PATH, file)
		print(("  removing %-30s:\t" % path), end='')
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			ret = ret + 1
			continue
		print("Complete")

	# Clean up logs/ directory
	print(("\nCleaning directory: %s..." % LOG_PATH))
	log_dir = os.listdir(LOG_PATH)
	for file in log_dir:
		path = os.path.join(LOG_PATH, file)
		print(("  removing %-30s:\t" % path), end='')
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
	chrome_path = config_data.getChromePath()

	if chrome_path is None:
		print("No preferred browser detected. Please open translation files \
			manually or input a path for chrome.exe file in user_config.json")
	else:
		path_trans = TRANS_PATH + "t%s_%d.html" % (series, ch)
		try:
			if platform.system() == "Darwin":
				chrome = 'open -a %s %s' % chrome_path
			if platform.system() == "Windows":
				chrome = chrome_path + r' %s'
			if platform.system() == "Linux":
				chrome = chrome_path + r' %s'

			google_chrome = webbrowser.get(chrome)
			google_chrome.open('file://' + os.path.realpath(path_trans))
		except OSError:
			print("\n[Error] The chrome browser [%s] does not exist. \
				Skipping" % chrome_path)
		except Exception:
			print("\n[Error] Cannot open Google Chrome [%s]. \
				Skipping" % chrome_path)

#============================================================================
#  Web scraping functions
#============================================================================
def getSeriesUrl(series):
	"""-------------------------------------------------------------------
		Function:		[getSeriesUrl]
		Description:	Returns the base url for the series
		Input:
		  [series]		The series to build url for
		Return: 		The full URL of the page containing chapter [ch] of
						[series] or just the series index URL if ch is None
		------------------------------------------------------------------
	"""
	global config_data

	# Build the url for this series table of contents page
	base_url = config_data.getHostUrl(config_data.getSeriesHost(series))
	series_code = config_data.getSeriesCode(series)
	series_url = base_url + series_code
	return series_url

def getChapterUrl(series, ch, globals_pkg):
	"""-------------------------------------------------------------------
		Function:		[getChapterUrl]
		Description:	Returns the complete url for the series and chapter
		Input:
		  [series]		The series to build url for
		  [ch]			The chapter to build url for
		  [globals_pkg]	Globals package
		Return: 		The full URL of the page containing chapter [ch] of
						[series] or just the series index URL if ch is None
		------------------------------------------------------------------
	"""
	# Unpack the needed globals
	config_data = globals_pkg.config_data
	page_table = globals_pkg.page_table

	# Build the url for this chapter
	base_url = config_data.getHostUrl(config_data.getSeriesHost(series))
	series_code = config_data.getSeriesCode(series)
	chapter_code = str(ch) if page_table is None else page_table[int(ch)-1]
	series_url = base_url + series_code + "/" + chapter_code

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
		print("Defaulting to deciding as UTF8")
		data = source.decode('utf8')

	return data

#============================================================================
#  Writer functions
#============================================================================
def writeRaw(series, ch, content):
	"""-------------------------------------------------------------------
		Function:		[writeRaw]
		Description:	Write raw to raw file
		Input:
		  [series]		The series to write raw for
		  [ch]			The chapter number to write raw for
		  [content]		The (raw) content to write, a list
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

def writeTrans(series, ch, globals_pkg):
	"""-------------------------------------------------------------------
		Function:		[writeTrans]
		Description:	Write translations to trans file
		Input:
		  [series]		The series to write translation for
		  [ch]			The chapter number to write translation for
		  [globals_pkg]	Globals package
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Unpack necessary globals
	series_dict = globals_pkg.series_dict
	config_data = globals_pkg.config_data

	# Initialize trans_file
	try:
		trans_name = "t%s_%d.html" % (series, ch)
		trans_file = io.open(os.path.join(TRANS_PATH, trans_name), 
			mode='w', 
			encoding='utf8'
		)
	except Exception:
		print(("[Error] Error opening translation file [%s]" % trans_name))
		print("Exiting...")
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
		print("Exiting...")
		return 1

	# Open log file
	try:
		log_name ="l%s_%d.log" % (series, ch)
		log_file = io.open(os.path.join(LOG_PATH, log_name), mode='w', encoding='utf8')
	except Exception:
		print("[Error] Error opening log file [%s]... " % log_name, end='')
		print("Proceeding without logs")
		log_file = open(os.devnull, 'w')

	# Initialize HTML Writer
	skeleton_path = RESOURCE_PATH + "skeleton.html"
	html_writer = htmlwriter.HtmlWriter(series_dict, log_file, skeleton_path)
	html_writer.setPageTitle(series, ch)
	html_writer.setChapterTitle(config_data.getSeriesTitle(series))
	html_writer.setChapterNumber(str(ch))

	# Count number of lines in raw source file
	raw_list = []
	for line in raw_file: 
		raw_list.append(line)

	num_lines = len(raw_list)
	line_num = 0
	for line in tqdm(raw_list, total=num_lines):
		line_num += 1
		# Skip blank lines
		if line != '\n':
			# Check raw text against dictionary and replace matches
			log_file.write("\n[L%d] Processing non-blank line..." % line_num)
			html_writer.insertLine(line, config_data.getSeriesLang(series))
		html_writer.insertBlankLine()

	# Write to trans file
	resource_string = html_writer.getResourceString()
	trans_file.write(resource_string)

	# Close all files file
	print(("Downtrans [t%s_%s.html] complete!" % (series, ch)))
	raw_file.close()
	trans_file.close()
	log_file.close()
	return 0

# =========================[ Script ]=========================
def batch_procedure(series, ch_queue, globals_pkg):
	"""-------------------------------------------------------------------
		Function:		[batch_procedure]
		Description:	Does the default procedure on each chapter in the list
						of [chapters]
		Input:
		  [series]	 	The series for which to downtrans chapter
		  [ch_queue] 	The list of chapter numbers to downtrans
		  [globals_pkg]	Globals package
		Return:			N/A
		------------------------------------------------------------------
	"""
	print(("Downtransing %s chapters: %s" % (series, str(ch_queue))))
	print("This may take a minute or two...")

	# Multiprocess queue of chapters requested
	pool = mp.Pool(processes=mp.cpu_count())
	args = [(series, ch, globals_pkg) for ch in ch_queue]

	results = pool.imap_unordered(_default_procedure, args)
	pool.close()
	pool.join()

	print("\nError Report (Consider redownloading erroneous chapters w/ -O flag)")
	ret_codes = list(results)
	for i in range(0, len(ret_codes)):
		status = "Success" if ret_codes[i] == 0 else "Failure"
		print("\tChapter %-5s: %s" % (ch_queue[i], status))

def _default_procedure(args):
	""" Simple wrapper method for pooling default_procedure """
	return default_procedure(*args)

def default_procedure(series, ch, globals_pkg):
	"""-------------------------------------------------------------------
		Function:		[default_procedure]
		Description:	Downloads and saves a raw for chapter [ch] of series 
						[series] and translates chapter with the dict 
						associated with [series]
		Input:
		  [series]		The series for which to downtrans chapter
		  [ch]			The integer indicating which chapter to downtrans
		  [globals_pkg]	Globals package
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Ret code: 0 - success, non-0 - failure
	ret = 0

	# Write the raw file if it doesn't already exist for this chapter
	raw_name = "r%s_%d.txt" % (series, ch)
	raw_chapter_path = os.path.join(RAW_PATH + raw_name)
	if not os.path.exists(raw_chapter_path) or os.path.getsize(raw_chapter_path) == 0:
		# Fetch the html source code
		url = getChapterUrl(series, ch, globals_pkg)
		config_data = globals_pkg.config_data
		html = fetchHTML(url, config_data.getSeriesLang(series))
		if html is None:
			return 1

		# Parse out relevant content from the website source code
		html_parser = globals_pkg.html_parser
		title = html_parser.parseTitle(html)
		content = [title, u'\n'] + html_parser.parseContent(html)
		ret += writeRaw(series, ch, content)

	# Write translation as HTML
	ret += writeTrans(series, ch, globals_pkg)
	return ret


def main():
	start = timer()
	# Declare relevant globals
	global config_data

	#Initialize config data from user_config.json
	initConfig()

	# Fetch arguments from parser
	parser = initArgParser()
	args = parser.parse_args()
	# Initialize arguments
	mode_batch	= args.batch
	mode_single = args.one
	series 		= args.series
	ch_start	= args.start
	ch_end 		= args.end

	# Create subdirectories if they don't already exist
	initEssentialPaths()
	# Initialize the HTML parser corresponding to the host of this series
	initHtmlParser(config_data.getSeriesHost(series))
	# Initialize the series page table according to series host
	initPageTable(series)
	# Initialize series dictionary
	initDict(series)

	# Package the finished globals as a Python equivalent of a C-struct
	globals_pkg = GlobalsPackage()
	globals_pkg.packGlobal("config_data")
	globals_pkg.packGlobal("html_parser")
	globals_pkg.packGlobal("series_dict")
	globals_pkg.packGlobal("page_table")

	# Different execution paths depending on mode
	if mode_batch:
		chapters = list(range(ch_start, ch_end+1))
		batch_procedure(series, chapters, globals_pkg)
		openBrowser(series, ch_start)
	elif mode_single:
		err_code = default_procedure(series, ch_start, globals_pkg)
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
	return 0

if __name__ == '__main__':
	# Check python version. Only run this script w/ Python 3
	if not sys.version_info[0] == 3:
		print("[Error] Must run this script w/ Python 3.X.X")
	main()

