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

import sys, os, io 					# System operations
import winsound 					# Sounc alarm
import re 							# Regex for parsing HTML

import itertools as it 				# Iteration tool
import argparse as argp 			# Parse input arguments
import multiprocessing as mp 		# Multiprocessing tasks
import googletrans as gt 			# Translation API
import urllib2 as ureq				# Fetch URL Requests



# =======================[ WN Constants ]========================
syosetu_url = "https://ncode.syosetu.com/"
# Put series to (code, dict) mappings here 
Series = {
	"Kanna": 		('n3877cq',	"kanna.dict"),
	"ChiyuMahou": 	('n2468ca', "chiyumahou.dict")
}
NCODE = 0				# The position of the NCode portion of the Series map
DICT = 1				# The position of the dict portion of the Series map

# Read chapter content only? Or include author comments in translation too?
content_only = False	



# =========================[ Constants ]=========================
# Sound alarm constants
ALARM_DUR = 100 	# milliseconds (ms)
ALARM_FREQ = 600 	# hertz (Hz)

# File paths
DICT_PATH = "./dicts/"
RAW_PATH = "./raws/"
TRANS_PATH = "./trans/"

# Format of the divider for .dict file
DIV = " --> "



# =========================[ Functions ]=========================
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
				print("\n[Complete] Cleaned all but %d files. Exiting..." % r)
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

	# Series mapping does not exist in Series dictionary
	if not args.series in Series:
		parser.error("The series '"+str(args.series)+"' does not exist in the source code mapping")
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
		dict_name = Series[series][DICT]
		dict_file = io.open(os.path.join(DICT_PATH, dict_name), mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening dictionary file. Make sure '.dict' exists in the dict/ folder")
		print("\nExiting...")
		sys.exit(1)

	# Parse the mappings into a list
	map_list = []
	for line in dict_file:
		# Skip unformatted/misformatted lines
		if not DIV in line:
			continue

		line = line[:-1]	# Ignore newline '\n' at the end of the line
		mapping = line.split(DIV)
		map_list.append(mapping)

	wn_dict = OrderedDict(map_list)
	return wn_dict

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
	return syosetu_url + Series[series][NCODE] + "/" + str(ch) + "/"

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
	# Request NCode page
	try:
	    response = ureq.urlopen(url)
	# Some error has occurred
	except Exception as e:
		print(str(e))
		print("[Error] Could not get response from <%s>" % url)
		print("  Make sure this URL exists")
		print("\nSkipping chapter %d..." % url.split('/')[-2])
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
			content.append(u'\n')
		else:
			content.append(line)
		content.append(u'\n')

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
		print("[Error] Error opening raw file [%s]" % raw_name)
		print("\nExiting...")
		sys.exit(1)

	# Write to raw
	for line in content:
		raw_file.write(line)
		raw_file.write(u'\n')

	# Close raw file
	raw_file.close()

def writeTrans(series, ch, wn_dict):
	"""-------------------------------------------------------------------
		Function:		[writeTrans]
		Description:	Write translations to trans file
		Input:
		  [series]	The series to write translation for
		  [ch]		The chapter number to write translation for
		  [wn_dict]	The Web Novel dictionary to use
		  [content]	The (raw) content to translate and write, a list
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Initialize translator
	translator = gt.Translator()

	# Initialize trans_file
	try:
		trans_name = "t%s_%d.txt" % (series, ch)
		trans_file = io.open(os.path.join(TRANS_PATH, trans_name), mode='w', encoding='utf8')
	except Exception:
		print("[Error] Error opening trans file [%s]" % trans_name)
		print("\nExiting...")
		sys.exit(1)

	# Open raw_file
	try:
		raw_name = "r%s_%d.txt" % (series, ch)
		raw_file = io.open(os.path.join(RAW_PATH, raw_name), mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening raw file [%s]" % raw_name)
		print("\nExiting...")
		sys.exit(1)

	# Count number of lines in raw source file
	num_lines = 0
	raw_list = []
	for line in raw_file: 
		num_lines += 1
		raw_list.append(line)

	#import pdb; pdb.set_trace()
	for line in tqdm(raw_list, total=num_lines):
		# Skip blank lines
		if line == u'\n':
			trans_file.write(u'\n')
			continue

		# Check raw text against dictionary and replace matches
		line = line + u'\n'
		prepped = line
		for entry in wn_dict:
			prepped = prepped.replace(entry, wn_dict[entry])

		# Feed prepped line through translator
		#import pdb; pdb.set_trace()
		try:
			translated = translator.translate(prepped, src='ja', dest='en')
		except ValueError as e:
			import pdb; pdb.set_trace()
			print(str(e))
			print("Skipping...")
			trans_file.write("[ERROR LINE]")
			continue
		except AttributeError as e:
			print("[Error] Whoops, something happened with googletrans. This happens sometimes so just try again.")
			print("Retrying...")
			raw_file.close()
			trans_file.close()
			return writeTrans(series, ch, wn_dict)

		translated = translated.text + "\n"
		trans_file.write(translated)

	# Close all files file
	raw_file.close()
	trans_file.close()


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
	pool = mp.Pool(processes=mp.cpu_count())
	args = [(series, ch) for ch in ch_queue]

	results = pool.imap_unordered(_default_procedure, args)
	pool.close()
	pool.join()


def _default_procedure(args):
	""" Simple wrapper method for pooling default_procedure """
	default_procedure(*args)

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
	# Fetch the html source code
	url = getSeriesURL(series, ch)
	html = fetchHTML(url)

	# Parse out relevant content from the website source code
	title = parseTitle(html)
	content = [title] + parseContent(html)
	#import pdb; pdb.set_trace()

	# Write raw_file
	writeRaw(series, ch, content)

	# Translate and write trans_file
	wn_dict = initDict(series)
	writeTrans(series, ch, wn_dict)


def main():
	start = timer()
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
	if not os.path.exists(RAW_PATH):
		os.makedirs(RAW_PATH)
	if not os.path.exists(TRANS_PATH):
		os.makedirs(TRANS_PATH)

	# Different execution paths depending on mode
	if mode_batch:
		chapters = list(range(ch_start, ch_end+1))
		batch_procedure(series, chapters)
	elif mode_single:
		default_procedure(series, ch_start)
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
		print("[Error] Please run this ")
	main()

