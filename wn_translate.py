# -*- coding: utf-8 -*-

# Imports
import sys, os, io
import winsound

from collections import OrderedDict	# Ordered Dictionary
from tqdm import tqdm				# Progress bar
import googletrans as gt 			# Translation API

# Constants
expected_n_args = 1
# Sound alarm constants
duration = 50 # milliseconds
freq = 600 # Hz

# File paths
dict_path = "./dicts/"
raw_path = "./source_raw.txt"
trans_path = "./source_trans.txt"

# Format of the divider for .dict file
divider = " --> "

# ============[ Functions ]============
def printUsage():
	""" Prints usage information """
	print("\n------------------------------")
	print("Usage:\t python wn_translate.py [dict_file]")
	print("  [dict_file]  The dictionary file (.dict) in the ./dicts folder to use.")

def verifyArgs():
	"""	Verifies arguments are valid """
	arguments = sys.argv;
	num_args = len(arguments) - 1

	# Too many or too few arguments
	if not num_args == expected_n_args:
		print("[Error] Expected 1 argument but %d given" % num_args)
		printUsage()
		print("\nExiting...")
		sys.exit()

def initFiles():
	""" Description:
			Initializes and returns dict, raw, and output files 
		Input:
			None
		Return:
			A 3-tuple consisting of the opened (1) dictionary file, 
			(2) raw source file, and (3) translation output file
	"""
	# Open dict file in read mode
	dict_file = None

	try:
		dict_file = io.open(os.path.join(dict_path, sys.argv[1]), mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening dictionary file")
		print("\t(1) Make sure argument is in the form <file_name>.dict")
		print("\t(2) Make sure this file exists in the ./dicts directory ")
		print("\nExiting...")
		sys.exit()

	# Open raw source file in read mode
	raw_file = None
	try:
		raw_file = io.open(raw_path, mode='r', encoding='utf8')
	except Exception:
		print("[Error] Error opening raw source file")
		print("\t(1) Make sure the file [source_raw.txt] exists in the same directory as this script")
		print("\t(2) Make sure it has your untranslated web novel chapter content")
		print("\nExiting...")
		sys.exit()

	if dict_file == None or raw_file == None:
		print("[Error] Something went wrong when opening dict file or raw source file")
		print("\nExiting...")
		sys.exit()

	# Open output file in write mode
	trans_file = io.open(trans_path, mode='w', encoding='utf8')

	return (dict_file, raw_file, trans_file)

def initDict(dict_file):
	""" Description:
			Initializes and returns the dictionary from .dict file 
		Input:
			[dict_file]		the dictionary file (.dict)
		Return:
			a dict() structure with the mappings indicated in dict_file
	"""
	map_list = []
	for line in dict_file:
		# Skip unformatted/misformatted lines
		if not divider in line:
			continue

		line = line[:-1]	# Ignore newline '\n' at the end of the line
		mapping = line.split(divider)
		map_list.append(mapping)

	wn_dict = OrderedDict(map_list)
	return wn_dict

def translate(raw_file, trans_file, wn_dict):
	""" Description:
			Applies mappings defined in wn_dict to raw text before putting the
			post-map raw text through a translator. Writes resulting text directly
			into trans_file
		Input:
			[raw_file]		The raw source file (.txt)
			[trans_file]	The translated file outputted (.txt)
			[wn_dict]		The dictionary to use for preparing raw text
		Output:
			None. Output can be found in the trans_file text file
	"""
	# Initialize translator
	translator = gt.Translator()

	# Count number of lines in raw source file
	num_lines = 0
	raw_list = []
	for line in raw_file: 
		num_lines += 1
		raw_list.append(line)

	#import pdb; pdb.set_trace()
	for line in tqdm(raw_list, total=num_lines):
		# Skip blank lines
		if line[0] == u'\n':
			trans_file.write(u'\n')
			continue

		#import pdb; pdb.set_trace()
		# Check raw text against dictionary and replace matches
		prepped = line
		for entry in wn_dict:
			prepped = prepped.replace(entry, wn_dict[entry])

		# Feed prepped line through translator
		try:
			translated = translator.translate(prepped, src='ja', dest='en').text
			if ' / ' in translated:
				translated = translated.replace(' / ', '/')
		except ValueError as e:
			print("\n[Error] The length of translation exceeds what's permitted by googletrans API")
			
			print("\nExiting...")
			sys.exit()
		except AttributeError as e:
			print("[Error] Whoops, something happened with googletrans. This happens sometimes so just try again.")

			print("\nExiting...")
			sys.exit()

		translated = translated + "\n"
		trans_file.write(translated)




# ============[ Script ]============
def main():
	# Verify arguments
	verifyArgs()

	# Initialize files
	(dict_file, raw_file, trans_file) = initFiles()

	# Initialize Web Novel's user-customized dictionary
	wn_dict = initDict(dict_file)
	dict_file.close()

	# Translate
	print("\nTranslating....")
	translate(raw_file, trans_file, wn_dict)
	raw_file.close()
	trans_file.close()

	print("\n[Complete] Check output file (%s)" % trans_path)
	winsound.Beep(freq, duration)

	return 0

if __name__ == '__main__':
	main()

