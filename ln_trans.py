# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[ln_downtrans.py]
  Description:	This module translates existing raws using dicts
  				without the need to download
"""

# =========================[ Imports ]==========================
from timeit import default_timer as timer 	# Timer
from collections import OrderedDict			# Ordered Dictionary
from tqdm import tqdm						# Progress bar

import sys, os, io 					# System operations
import winsound 					# Sounc alarm
import time 						# For sleeping thread between retries
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
	"ChiyuMahou": 	('n2468ca', "chiyumahou.dict"),
	"Glitch":		('n9078bd', "glitch.dict"),
	"LV999":		('n7612ct', "lv999.dict")
}
NCODE = 0				# The position of the NCode portion of the Series map
DICT = 1				# The position of the dict portion of the Series map

# Read chapter content only? Or include author comments in translation too?
content_only = False	



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

	# Positional arguments
	parser.add_argument('raw_name', 
		help="Name of the raw file to use")
	parser.add_argument('dict_name',
		help="Name of the dict file to use")

	return parser

def initDict(dictionary):
	"""-------------------------------------------------------------------
		Function:		[initDict]
		Description:	Initializes and returns the dictionary from .dict file 
		Input:
		 [dictionary]	The name of the .dict file (w/out .dict)
		Return:			Returns a dict() structure with the mappings indicated 
						in dict_file
		------------------------------------------------------------------
	"""
	# Open dict file in read mode
	try:
		dict_name = dictionary + ".dict"
		dict_file = io.open(os.path.join(DICT_PATH, dict_name), mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening dictionary file. Make sure '.dict' exists in the dict/ folder... ")
		print("Proceeding without special translations")
		return {}

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
	dict_file.close()
	return wn_dict

def writeTrans(rawfile_name, wn_dict):
	"""-------------------------------------------------------------------
		Function:		[writeTrans]
		Description:	Write translations to trans file
		Input:
		  [raw_name]	The name of the raw to translate
		  [wn_dict]		The Web Novel dictionary to use
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Initialize trans_file
	try:
		trans_name = "t%s.txt" % (rawfile_name)
		trans_file = io.open(os.path.join(TRANS_PATH, trans_name), mode='w', encoding='utf8')
	except Exception:
		print("[Error] Error opening trans file [%s]" % trans_name)
		print("\nExiting...")
		return 1

	# Open raw_file
	try:
		raw_name = "%s.txt" % (rawfile_name)
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

	#import pdb; pdb.set_trace()
	ret = 0
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

		# Feed prepped line through translator max 5 tries
		#import pdb; pdb.set_trace()
		tries = 0
		while True:
			try:
				translator = gt.Translator()
				translated = translator.translate(prepped, src='ja', dest='en')
				translated = translated.text + "\n"
				break
			except ValueError as e:
				#import pdb; pdb.set_trace()
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

	# Close all files file
	print("Downtrans [t%s.txt] complete!" % (rawfile_name))
	raw_file.close()
	trans_file.close()
	return ret


# =========================[ Script ]=========================
def default_procedure(raw_name, dict_name):
	"""-------------------------------------------------------------------
		Function:		[default_procedure]
		Description:	Downloads and saves a raw for chapter [ch] of series 
						[series] and translates chapter with the dict 
						associated with [series]
		Input:
		  [raw_name]	The name of the raw to translate
		  [dict_name]	The name of the dict file to use
		Return:			N/A
		------------------------------------------------------------------
	"""
	# Ret code: 0 - success, non-0 - failure
	ret = 0

	# Translate and write trans_file
	wn_dict = initDict(dict_name)
	ret += writeTrans(raw_name, wn_dict)

	return ret


def main():
	start = timer()
	# Fetch arguments from parser
	parser = initParser()
	args = parser.parse_args()

	raw_name = args.raw_name
	dict_name = args.dict_name

	# Create subdirectories if they don't already exist
	if not os.path.exists(RAW_PATH):
		os.makedirs(RAW_PATH)
	if not os.path.exists(TRANS_PATH):
		os.makedirs(TRANS_PATH)

	# Different execution paths depending on mode
	default_procedure(raw_name, dict_name)

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

