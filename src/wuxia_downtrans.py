# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[wuxia_downtrans.py]
  Description:	This module downloads and translates series from 
  				biquyun.com using custom dictionaries that make
  				the machine translation much more readable
"""

# =========================[ Imports ]==========================
from timeit import default_timer as timer 	# Timer
from collections import OrderedDict			# Ordered Dictionary
from tqdm import tqdm						# Progress bar
from pdb import set_trace					# Debugging
from stat import S_IREAD, S_IRGRP, S_IROTH 	# Changing file permissions

import sys, os, io 					# System operations
import winsound 					# Sounc alarm
import time 						# For sleeping thread between retries
import re 							# Regex for parsing HTML

import itertools as it 				# Iteration tool
import argparse as argp 			# Parse input arguments
import multiprocessing as mp 		# Multiprocessing tasks
import subprocess 					# Open file in preferred text editor
import googletrans as gt 			# Translation API
import urllib2 as ureq				# Fetch URL Requests
import ssl 							# For certificate authentication


# =======================[ WN Constants ]========================
biquyun_url = "https://www.biquyun.com/"
# Put series to (code, dict) mappings in user_config. The code is associated with the main 
# URL for the novel. For example, for Gate of God (GOG), the code is the last part of the
# URL: "https://www.biquyun.com/2_2794/"

# Important globals initialized from user_config.txt
series_map = {}
PREFERRED_READER_PATH = ""


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
TABLES_PATH = "./tables/"
LOG_PATH = "./logs/"

# Format of the divider for .dict file
DIV = " --> "

# The page table indexes the hashed url footer of each chapter with the chapter number
# according to the table of contents html page of the target series
page_table = []


# =========================[ Functions ]=========================
def initConfig():
	"""-------------------------------------------------------------------
		Function:		[initConfig]
		Description:	Initializes some important globals using user_config.txt
		Input:			None
		Return:			None
		------------------------------------------------------------------
	"""
	# If config file does not exist, create it and exit
	if not os.path.exists("./user_config.txt"):
		print("\n[Error] user_config file does not exist. Creating file skeleton...")
		try:
			config_file = io.open(os.path.join("./user_config.txt"), mode='w', encoding='utf8')
			config_file.write(u"PREFERRED_READER_PATH: notepad.exe\n\n")
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
				elif line[0] == "PREFERRED_READER_PATH:":
					global PREFERRED_READER_PATH
					PREFERRED_READER_PATH = line[1][:-1] if line[1][-1] == u'\n' else line[1]
					print("\nPreferred Reader: \'%s\'" % PREFERRED_READER_PATH)
				else:
					series = line[0]
					code = line[1][:-1] if line[1][-1] == u'\n' else line[1]
					series_map[series] = code
					print("Series: \'%s\' (Code=%s)" % (series, code))

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
	parser = argp.ArgumentParser(description="Download and run special translation on chapters directly from www.biquyun.com")

	# Mode flags are mutually exclusive: Either single or batch downtrans
	# or clean you folders or redownload/refresh a series's .table
	mode_flags = parser.add_mutually_exclusive_group(required=True)
	mode_flags.add_argument('-C', '--clean',
		action="store_true",
		help="Clean the /raw and /trans subdirectories"
		)
	mode_flags.add_argument('-R', '--refresh',
		action="store_true",
		help="Redownloads the .table for this series"
		)
	mode_flags.add_argument('-B', '--batch',
		action="store_true", 
		help="Downloads and translates a batch of chapters")
	mode_flags.add_argument('-O', '--one',
		action="store_true", 
		help="Downloads and translates one chapter")

	if len(sys.argv) > 1:
		args = sys.argv[1:]
		# Handle clean directory case
		if args[0] == '-C' or args[0] == '--clean':
			r = handleClean()
			if r == 0:
				print("\n[Success] /raws and /trans cleaned. Exiting...")
			else:
				print("\n[Complete] Cleaned all but %d files. Exiting..." % r)
			sys.exit(0)

	# Positional arguments
	parser.add_argument('series', 
		help="Which series to download and translate with a dictionary")
	# Handle refresh case
	args = sys.argv[1:]
	if args[0] == '-R' or args[0] == '--refresh':
		if len(args) <= 1:
			print("\n[Error] Please specify a series after the refresh flag. Exiting...")
			sys.exit(1)
		initPageTableFromWeb(args[1])
		print("\n[Success] .table refreshed for %s in /tables. Exiting..." % args[1])
		sys.exit(0)

	parser.add_argument('start',
		type=int,
		help="The chapter number to start downtrans process at")
	parser.add_argument('end',
		type=int,
		nargs='?',
		help="The chapter number to end downtrans process at")

	# Handle errors or address warnings
	args = parser.parse_args()

	# series_map mapping does not exist in series_map dictionary
	global series_map
	if not args.series in series_map:
		parser.error("The series '"+str(args.series)+"' does not exist in the series_map variable\n \
			   [Solution] Add a definition for '"+str(args.series)+"' in user_config.txt")
	# Batch command w/out 'end' chapter argument
	if args.batch and not args.end:
		parser.error("For batch downloads, both a start and end chapter are required")
	# Single commang w/ 'out' chapter argument
	elif args.one and args.end:
		print("[Warning] Detected flag -O for single download-translate but received both a 'start'\nand 'end' argument. Ignoring argument end=%d...." % args.end)
	# Chapter numbering starts at 1
	if args.start < 1:
		parser.error("Start chapter argument is a minimum of 1 [start=%d]" % args.start)
	# End chapter must be greater than start chapter
	if args.batch and not (args.start < args.end):
		parser.error("End chapter must be greater than start chapter [start=%d, end=%d]" % (args.start, args.end))
	# Check that this chapter exists
	global page_table
	num_chapters = len(page_table)
	if args.start > num_chapters or args.end > num_chapters:
		parser.error("Page table for %s only contains up to chapter %d" % (args.series, num_chapters))
		sys.exit(2)

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

	print("\nCleaning directory: %s..." % RAW_PATH)
	raw_dir = os.listdir(RAW_PATH)
	for file in raw_dir:
		path = os.path.join(RAW_PATH, file)
		print "\tremoving [%s]...\t" % path,
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			retcode = retcode + 1
			continue
		print("Complete")

	print("\nCleaning directory: %s..." % TRANS_PATH)
	trans_dir = os.listdir(TRANS_PATH)
	for file in trans_dir:
		path = os.path.join(TRANS_PATH, file)
		print "\tremoving [%s]...\t" % path,
		try:
			os.remove(path)
		except OSError:
			print("Failed")
			retcode = retcode + 1
			continue
		print("Complete")

	print("\nCleaning directory: %s..." % LOG_PATH)
	log_dir = os.listdir(LOG_PATH)
	for file in log_dir:
		path = os.path.join(LOG_PATH, file)
		print "\tremoving [%s]...\t" % path,
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
	dict_name = series.lower() + ".dict"
	try:
		dict_file = io.open(os.path.join(DICT_PATH, dict_name), mode='r', encoding='utf-8')
	except Exception:
		print("[Error] Unable to open dictionary file for the series %s" % series)
		print("Creating empty '%s' in dict/ folder..." % dict_name)
		try:
			dict_file = io.open(os.path.join(DICT_PATH, dict_name), mode='w', encoding='utf-8')
			dict_file.close()
			print("  [Success] Created %s in \'dict/\'" % dict_name)
		except Exception:
			print("  [Error] Trouble creating %s. Try making it manually" % dict_name)

		print("\nProceeding without special translations...")
		return ({}, {})

	# Parse the mappings into a list
	rawToIndx = []
	indxToSubst = []
	subst_indx = 1
	for line in dict_file:
		# Skip unformatted/misformatted lines
		if not DIV in line:
			continue

		line = line[:-1]	# Ignore newline '\n' at the end of the file
		(raw_txt, subst_txt) = line.split(DIV)
		subst_str = "RPLC_%d" % subst_indx
		rawToIndx.append((raw_txt, subst_str))
		indxToSubst.append((subst_str, subst_txt))

		subst_indx = subst_indx + 1

	raw_dict = OrderedDict(rawToIndx)
	indx_dict = OrderedDict(indxToSubst)

	dict_file.close()
	return (raw_dict, indx_dict)


def initPageTableFromFile(series):
	"""-------------------------------------------------------------------
		Function:		[initPageTableFromFile]
		Description:	Initializes the page table for this series from 
						a preexisting .table file
		Input:			
		  [series]		The series to build the page table for
		Return: 		None, initializes a global list page_table
		------------------------------------------------------------------
	"""
	global page_table
	page_table = []
	try:
		table_name = "%s.table" % series
		table_file = io.open(os.path.join(TABLES_PATH, table_name), mode='r', encoding='utf8')
		for line in table_file:
			if line is u'\n':
				continue
			page_table.append(line[:-1])
	except Exception:
		print("[Error] Error opening table file [%s]" % table_name)
		print("\nExiting...")
		sys.exit(4)


def initPageTableFromWeb(series):
	"""-------------------------------------------------------------------
		Function:		[initPageTableFromWeb]
		Description:	Initializes the and saves the page table for this
						series as a file for future reference
		Input:			
		  [series]		The series to build the page table for
		Return: 		None, initializes a global list page_table
		------------------------------------------------------------------
	"""
	global series_map
	if not series in series_map:
		print("[Error] Config for [series=%s] does not exist. Exiting..." % series)
		sys.exit(1)

	series_url = biquyun_url + series_map[series] + "/"
	page_html = fetchHTML(series_url)
	page_table = re.findall(r'<a href="/' + re.escape(series_map[series])
		+ r'/(.*?)\.html">', page_html)

	# Save to .table file
	try:
		table_name = "%s.table" % series
		table_path = os.path.join(TABLES_PATH, table_name)
		table_file = io.open(table_path, mode='w', encoding='utf8')
		for entry in page_table:
			table_file.write(entry + u'\n')
	except Exception:
		print("[Error] Error opening table file [%s]" % table_name)
		print("\n Exiting...")
		sys.exit(4)

	# Close file as read only to prevent external modifications
	table_file.close()
	os.chmod(table_path, S_IREAD|S_IRGRP|S_IROTH)
	return


def getSeriesURL(series, ch, base_url):
	"""-------------------------------------------------------------------
		Function:		[getSeriesURL]
		Description:	Returns the complete url for the series and chapter
		Input:			
		  [series]		The series to build url off of
		  [ch]			The chapter to build url off of
		  [base_url]	The base URL holding the table of contents of series
		Return: 		The full URL of the page containing chapter [ch] of
						[series]
		------------------------------------------------------------------
	"""
	# If cannot initialize page table for some reason, exit
	global page_table
	if len(page_table) == 0:
		initPageTableFromFile(series)

		if len(page_table) == 0:
			print("[Error] Error, page table uninitialized")
			sys.exit(2)

	series_url = base_url + "/" + page_table[ch-1] + ".html"
	return series_url

def fetchHTML(url):
	"""-------------------------------------------------------------------
		Function:		[fetchHTML]
		Description:	Tries to prompt a response url and return the received
						HTML content as a UTF-8 decoded string
		Input:			
		  [url]		The url to make the request to
		Return: 		The HTML content of the given website address
		------------------------------------------------------------------
	"""
	tries = 0
	while True:
		try:
			headers = { 'User-Agent' : 'Mozilla/5.0' }
			request = ureq.Request(url, None, headers)
			response = ureq.urlopen(request, context=ssl._create_unverified_context())
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
	data = source.decode('gbk')
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
	title = re.findall(r'<div class="bookname">\r\n\t\t\t\t\t<h1>(.*?)</h1>', html)
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
	lines = re.findall(r'&nbsp;&nbsp;&nbsp;&nbsp;(.*?)<', html)
	for line in lines:
		content.append(line)
		content.append(u'\n')

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
		print("[Error] Error opening raw file [%s]" % raw_name)
		print("\nExiting...")
		return 1

	# Write to raw
	raw_file.write(u"CHAPTER %d\n\n" % ch)
	for line in content:
		raw_file.write(line)
		raw_file.write(u'\n')

	# Close raw file
	raw_file.close()
	return 0

def writeTrans(series, ch, raw_dict, indx_dict, log_file):
	"""-------------------------------------------------------------------
		Function:		[writeTrans]
		Description:	Write translations to trans file
		Input:
		  [series]		The series to write translation for
		  [ch]			The chapter number to write translation for
		  [raw_dict]	The dict mapping raw to indices
		  [indx_dict]	The dict mapping indices to true substitutions
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Initialize trans_file
	try:
		trans_name = "t%s_%d.txt" % (series, ch)
		trans_file = io.open(os.path.join(TRANS_PATH, trans_name), mode='w', encoding='utf8')
	except Exception:
		print("[Error] Error opening trans file [%s]" % trans_name)
		print("\nExiting...")
		return 1

	# Open raw_file
	try:
		raw_name = "r%s_%d.txt" % (series, ch)
		raw_file = io.open(os.path.join(RAW_PATH, raw_name), mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening raw file [%s]" % raw_name)
		print("\nExiting...")
		return 1

	# Count number of lines in raw source file
	num_lines = 0
	raw_list = []
	for line in raw_file: 
		num_lines += 1
		raw_list.append(line)

	ret = 0
	line_num = 0
	for line in tqdm(raw_list, total=num_lines):
		line_num += 1
		# Pick out specific problematic line for debug purposes
		# Skip blank lines
		if line == u'\n':
			trans_file.write(u'\n')
			continue

		# Check raw text against dictionary and replace matches
		log_file.write(u"\n[L%d] Processing non-blank line..." % line_num)
		line = line + u'\n'
		prepped = line
		for entry in raw_dict:
			if entry in prepped:
				log_file.write(u"\n\tDetected token %s in line. Replacing with %s" % (entry, raw_dict[entry]))
				prepped = prepped.replace(entry, raw_dict[entry])
				log_file.write(u"\n\tPrepped=%s" % prepped)

		# Feed prepped line through translator max 5 tries
		tries = 0
		while True:
			try:
				translator = gt.Translator()
				translated = translator.translate(prepped, src='zh-cn', dest='en')
				translated = translated.text + "\n"
				log_file.write(u"\n\tUnprocessed Translation: %s" % translated)
				for k, v in [(k, indx_dict[k]) for k in reversed(indx_dict)]:
					if k in translated:
						log_file.write(u"\n\tReplacing token...")
						log_file.write(u"\n\t\t%s ==> %s" % (k, v))
						translated = translated.replace(k, v)
				break
			except ValueError as e:
				log_file.write(u"\n[Error line] Line = %d" % line_num)
				print(str(e))
				print("Exiting...")
				return 1
			except AttributeError as e:
				tries += 1
				print("\n[Error] Timeout on googletrans. Retrying [tries=%d]..." % tries)

			if tries == MAX_TRIES:
				print("\n[Error] Max tries reached. Couldn't translate line. Skipping....")
				translated = "[Error line]\n"
				ret = 1
				break

		# Write to file
		trans_file.write(translated)
		#trans_file.write(roma(line) + u'\n')

	# Close all files file
	print("Downtrans [t%s_%s.txt] complete!" % (series, ch))
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
	print("Downtransing %s chapters: %s" % (series, str(ch_queue)))
	print("This may take a minute or two...")

	# Multiprocess queue of chapters requested
	global series_map
	base_url = biquyun_url + series_map[series]
	pool = mp.Pool(processes=mp.cpu_count())
	args = [(series, ch, base_url) for ch in ch_queue]

	results = pool.imap_unordered(_default_procedure, args)
	pool.close()
	pool.join()

	print("\nError Report (Consider redownloading erroneous chapters w/ -O flag)")
	ret_codes = list(results)
	for i in range(0, len(ret_codes)):
		if ret_codes[i] == 0:
			print("\tChapter %s: SUCCESS" % ch_queue[i])
		else:
			print("\tChapter %s: FAILURE" % ch_queue[i])

def _default_procedure(args):
	""" Simple wrapper method for pooling default_procedure """
	return default_procedure(*args)

def default_procedure(series, ch, base_url):
	"""-------------------------------------------------------------------
		Function:		[default_procedure]
		Description:	Downloads and saves a raw for chapter [ch] of series 
						[series] and translates chapter with the dict 
						associated with [series]
		Input:
		  [series]	The series for which to downtrans chapter
		  [ch]		The integer indicating which chapter to downtrans
		  [base_url]The base URL containing the table of contents for series
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Ret code: 0 - success, non-0 - failure
	ret = 0

	# Write the raw file if it doesn't already exist for this series and chapter
	raw_chapter_path = RAW_PATH + "r%s_%d.txt" % (series, ch)
	if not os.path.exists(raw_chapter_path):
		# Fetch the html source code
		url = getSeriesURL(series, ch, base_url)
		html = fetchHTML(url)
		if html == None:
			return 1

		# Parse out relevant content from the website source code
		title = parseTitle(html)
		content = [title, u'\n'] + parseContent(html)
		ret += writeRaw(series, ch, content)

	# Translate and write trans_file
	(raw_dict, indx_dict) = initDict(series)
	# Open log file in write mode
	try:
		log_name ="l%s_%d.log" % (series, ch)
		log_file = io.open(os.path.join(LOG_PATH, log_name), mode='w', encoding='utf8')
	except Exception:
		print("[Error] Error opening log file... ")
		return -1
	ret += writeTrans(series, ch, raw_dict, indx_dict, log_file)
	log_file.close()

	return ret


def main():
	# Read config file
	start = timer()
	initConfig()

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
	if not os.path.exists(TABLES_PATH):
		os.makedirs(TABLES_PATH)

	# Initialize the series table file if it doesn't exist
	series_table = TABLES_PATH + "%s.table" % series
	if not os.path.exists(series_table) or os.path.getsize(series_table) == 0:
		print("No table file exists for this series... Creating a new table")
		initPageTableFromWeb(series)

	# Different execution paths depending on mode
	if mode_batch:
		# Run the batch downtrans procedure
		chapters = list(range(ch_start, ch_end+1))
		batch_procedure(series, chapters)
	elif mode_single:
		# Initialize page table
		initPageTableFromFile(series)

		# Run the default single chapter downtrans procedure
		global series_map
		base_url = biquyun_url + series_map[series]
		default_procedure(series, ch_start, base_url)
		
		# After done with the main procedure, automatically open file in Sublime
		path_raw = RAW_PATH + "r%s_%d.txt" % (series, ch_start)
		path_trans = TRANS_PATH + "t%s_%d.txt" % (series, ch_start)
		if len(PREFERRED_READER_PATH) == 0:
			print("No preferred reader detected. Please open translation files manually\
				or input a path for your preferred reader .exe file in user_config.txt")
		else:
			try:
				subprocess.Popen([PREFERRED_READER_PATH, path_raw])
				subprocess.Popen([PREFERRED_READER_PATH, path_trans])
			except OSError:
				print("\n[Error] The preferred reader [%s] does not exist. Skipping" % PREFERRED_READER_PATH)
			except Exception:
				print("\n[Error] Cannot open the preferred reader [%s]. Skipping" % PREFERRED_READER_PATH)
	else:
		print("[Error] Unexpected mode")
		sys.exit(1)

	# Print completion statistics
	print("\n[Complete] Check output files in %s" % TRANS_PATH)
	elapsed = timer() - start
	if elapsed > 60:
		elapsed = elapsed / 60
		print("  Elapsed Time: %.2f min" % elapsed)
	else:
		print("  Elapsed Time: %.2f sec" % elapsed)

	winsound.Beep(ALARM_FREQ, ALARM_DUR)
	return 0

if __name__ == '__main__':
	# Check python version. Only run this script w/ Python 2
	if not sys.version_info[0] == 2:
		print("[Error] Please run this with Python 2 instead of Python 3")
	main()

