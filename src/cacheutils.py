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
	pattern = re.compile(r"(.*):CURR=(\d*):MAX=(\d*)\n")
	with open(CACHE_PATH, 'r') as cache_file:
		for line in cache_file.readlines():
			match = pattern.fullmatch(line)
			if match:
				series_data = match.group(1)
				ch_curr = match.group(2)
				ch_max = match.group(3)

				# Skip repeat entries
				if series_data in cache_data:
					continue

				# Record cache data for this row
				cache_data[series_data] = (ch_curr, ch_max)

	return cache_data

def writeCacheData(series, l_series, ch_curr=0, ch_max=0):
	"""-------------------------------------------------------------------
		Function:		[writeCacheData]
		Description:	Writes/updates a series' recent ch cache data
		Input:			
			[series]	The series to write cache data for
			[ch_curr]	The current chapter downloaded by user for series
			[ch_max]	The most recent chapter available by author
		Return:			None
		------------------------------------------------------------------
	"""
	cache_data = readCacheData()
	cached_ch_curr = int(cache_data[series][0]) if series in cache_data else 0
	cached_ch_max  = int(cache_data[series][1]) if series in cache_data else 0
	cache_data[series] = (max(ch_curr, cached_ch_curr), max(ch_max, cached_ch_max))
	with open(CACHE_PATH, 'w') as cache_file:
		for entry in cache_data:
			if entry in l_series:
				(ch_curr, ch_max) = cache_data[entry]
				data = "%s:CURR=%s:MAX=%s\n" % (entry, ch_curr, ch_max)
				cache_file.write(data)