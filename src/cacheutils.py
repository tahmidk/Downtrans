# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[cacheutils.py]
  Description:	This module provides reading, interpreting
  				and writing of cache data
"""
import re
import os

# The cache file location
CACHE_PATH = os.path.join("../cmd_cache.txt")

def readCacheData():
	"""-------------------------------------------------------------------
		Function:		[readCacheData]
		Description:	Writes/updates a series' recent ch cache data
		Input:			None
		Return:			A dict mapping series to their most recent chapter
		------------------------------------------------------------------
	"""
	cache_data = {}

	# Read valid cache data into the data dict
	pattern = re.compile(r"(.*):(\d*)\n")
	with open(CACHE_PATH, 'r') as cache_file:
		for line in cache_file.readlines():
			match = pattern.fullmatch(line)
			if match:
				series_data = match.group(1)
				ch_data = match.group(2)
				if series_data in cache_data:
					print("[Warning] Duplicate cache entry for \'" + series_data \
						+ "\' detected... Ignoring")
					continue
				cache_data[series_data] = ch_data

	return cache_data

def writeCacheData(series, ch):
	"""-------------------------------------------------------------------
		Function:		[writeCacheData]
		Description:	Writes/updates a series' recent ch cache data
		Input:			
			[series]	The series to write cache data for
			[ch]		The most recent chapter downloaded for this series
		Return:			None
		------------------------------------------------------------------
	"""
	cache_data = readCacheData()
	cached_ch = int(cache_data[series]) if series in cache_data else 0
	cache_data[series] = max(ch, cached_ch)
	with open(CACHE_PATH, 'w') as cache_file:
		for entry in cache_data:
			data = entry + ":" + str(cache_data[entry]) + "\n"
			cache_file.write(data)