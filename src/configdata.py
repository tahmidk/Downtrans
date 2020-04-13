# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[configdata.py]
  Description:	This module initializes and holds data contained
  				in a given config JSON file customized by the user
"""
from tabulate import tabulate	# Print pretty tables
import functools as ft			# For reduction utility function
import json 					# JSON processing library
import cacheutils

# Length of dividers when printing
DIVIDER_BOLD = "=" * 120
DIVIDER_THIN = "-" * 120
L_PADDING = ' ' * 2

class ConfigData:
	#--------------------------------------------------------------------------
	#  ctor
	#--------------------------------------------------------------------------
	def __init__(self, config_path, verbose=False):
		"""-------------------------------------------------------------------
			Function:		[CONSTRUCTOR]
			Description:	Unpacks given config file in JSON format and makes 
							data accessible via several getters
			Input:			
			  [config_path]	File URL of user config JSON file
			------------------------------------------------------------------
		"""
		with open(config_path) as config_file:
			config = json.loads(config_file.read())

			# Initialize verbose print function
			print_verbose = verbose or config['verbose']
			self.vprint = print if print_verbose else lambda *a,**k: None
			# Initialize preferred browser path and counters
			self.__num_hosts = len(config['hosts'])
			self.__num_series = len(config['series'])
			browser = config['chrome_path']
			self.__browser = browser.rstrip() if len(browser) != 0 else None

			self.vprint("\n" + DIVIDER_BOLD)
			self.vprint("  chrome.exe Path: %s" % 
				self.__browser if self.__browser is not None else
				"UNSET (Do not automatically open translations in browser)"
			)
			self.vprint(DIVIDER_BOLD + "\n")

			# Initialize list of host websites
			self.initHostMap(config['hosts'])
			# Initialize list of series and their corresponding datas
			self.initSeriesMap(config['series'])

	#--------------------------------------------------------------------------
	#  Initializer functions
	#--------------------------------------------------------------------------
	def initHostMap(self, hosts):
		"""-------------------------------------------------------------------
			Function:		[initHostMap]
			Description:	Initializes this container's host map
			Input:			
			  [hosts]		JSON unpacked list of hosts
			Return:			None
			------------------------------------------------------------------
		"""
		self.__hosts = {}
		self.vprint(DIVIDER_BOLD)
		self.vprint(L_PADDING + "Detected Host Websites:")
		self.vprint(DIVIDER_THIN)
		for entry in hosts:
			self.__hosts[entry['host_name']] = entry['base_url']
			self.vprint(L_PADDING + "%-15s: %s" % (entry['host_name'], entry['base_url']))
		self.vprint(DIVIDER_BOLD + "\n")

	def initSeriesMap(self, series):
		"""-------------------------------------------------------------------
			Function:		[initSeriesMap]
			Description:	Initializes this container's series map
			Input:			
			  [series]		JSON unpacked list of series
			Return:			None
			------------------------------------------------------------------
		"""
		self.__series = {}
		self.vprint(DIVIDER_BOLD)
		self.vprint(L_PADDING + "Detected Series Data:")
		self.vprint(DIVIDER_BOLD)

		# This is just for aesthetics
		cache = cacheutils.readCacheData()
		ch_curr_len = max([len(ccurr) for (ccurr, cmax) in list(cache.values())])
		ch_max_len  = max([len(cmax) for (ccurr, cmax) in list(cache.values())])
		CURR_NDEF = "-" * max(ch_curr_len, 1)
		MAX_NDEF  = "-" * max(ch_max_len, 1)

		headers = ["Abbr", "Lang", "Code", "Host", "Title", "Current", "Latest"]
		data = []
		for entry in series:
			# Each series host must have a corresponding entry in self.__hosts
			if entry['host'] not in self.__hosts:
				print("[Error] No corresponding entry in the hosts JSON list \
					for \"host\": \"%s\" listed under the series \'%s\'!\n \
					Please insert an entry for this host and try again." %
					(entry['host'], entry['abbr'])
				)
				sys.exit(1)

			self.__series[entry['abbr']] = {
				'name': entry['name'],
				'lang': entry['lang'],
				'host': entry['host'],
				'code': entry['code']
			}

			ch_curr = cache[entry['abbr']][0] if entry['abbr'] in cache else CURR_NDEF
			ch_max  = cache[entry['abbr']][1] if entry['abbr'] in cache else MAX_NDEF
			row = (entry['abbr'],
				entry['lang'],
				entry['code'],
				entry['host'],
				entry['name'],
				ch_curr if int(ch_curr) > 0 else CURR_NDEF,
				ch_max if int(ch_max) > 0 else MAX_NDEF
			)
			data.append(row)

		# Print series config data as pretty table
		table_str = tabulate(data, headers=headers, numalign="left")
		self.vprint(L_PADDING + table_str.replace('\n', '\n'+L_PADDING))
		self.vprint(DIVIDER_BOLD + "\n")

	#--------------------------------------------------------------------------
	#  Accessor functions
	#--------------------------------------------------------------------------
	def getHosts(self):
		"""-------------------------------------------------------------------
			Function:		[getHosts]
			Description:	Fetches the user provided hosts data
			Input:			None
			Return:			Dict of hosts
			------------------------------------------------------------------
		"""
		return self.__hosts

	def getSeries(self):
		"""-------------------------------------------------------------------
			Function:		[getHosts]
			Description:	Fetches the user provided series data
			Input:			None
			Return:			Dict of series
			------------------------------------------------------------------
		"""
		return self.__series

	def getNumHosts(self):
		"""-------------------------------------------------------------------
			Function:		[getNumHosts]
			Description:	Fetches the number of user provided hosts
			Input:			None
			Return:			Number of hosts
			------------------------------------------------------------------
		"""
		return len(self.__hosts)

	def getNumSeries(self):
		"""-------------------------------------------------------------------
			Function:		[getNumHosts]
			Description:	Fetches the number of user provided series
			Input:			None
			Return:			Number of series
			------------------------------------------------------------------
		"""
		return len(self.__series)

	def getChromePath(self):
		"""-------------------------------------------------------------------
			Function:		[getChromePath]
			Description:	Fetches the user provided preferred browser path
			Input:			None
			Return:			Preferred browser local absolute path
			------------------------------------------------------------------
		"""
		return self.__browser

	def getSeriesTitle(self, series_abbr):
		"""-------------------------------------------------------------------
			Function:		[getSeriesLang]
			Description:	Fetches the given series language
			Input:			
			  [series_abbr] Abbreviated name of the series to look up
			Return:			Given series full title in string form
			------------------------------------------------------------------
		"""
		if self.seriesIsValid(series_abbr):
			return self.__series[series_abbr]['name']
		return None

	def getSeriesLang(self, series_abbr):
		"""-------------------------------------------------------------------
			Function:		[getSeriesLang]
			Description:	Fetches the given series language
			Input:			
			  [series_abbr] Abbreviated name of the series to look up
			Return:			Given series language in string form
			------------------------------------------------------------------
		"""
		if self.seriesIsValid(series_abbr):
			return self.__series[series_abbr]['lang']
		return None

	def getSeriesHost(self, series_abbr):
		"""-------------------------------------------------------------------
			Function:		[getSeriesHost]
			Description:	Fetches the given series language
			Input:			
			  [series_abbr]	Abbreviated name of the series to look up
			Return:			Given series host website in string form
			------------------------------------------------------------------
		"""
		if self.seriesIsValid(series_abbr):
			return self.__series[series_abbr]['host']
		return None

	def getSeriesCode(self, series_abbr):
		"""-------------------------------------------------------------------
			Function:		[getSeriesCode]
			Description:	Fetches the given series language
			Input:			
			  [series_abbr] Abbreviated name of the series to look up
			Return:			Given series web code in string form
			------------------------------------------------------------------
		"""
		if self.seriesIsValid(series_abbr):
			return self.__series[series_abbr]['code']
		return None

	def getHostUrl(self, host_name):
		"""-------------------------------------------------------------------
			Function:		[getHostUrl]
			Description:	Fetches the given host's base website URL
			Input:			
			  [host_name] 	Name of the host to look up
			Return:			Given host's URL in string form
			------------------------------------------------------------------
		"""
		if self.hostIsValid(host_name):
			return self.__hosts[host_name]

	#--------------------------------------------------------------------------
	#  Validation functions
	#--------------------------------------------------------------------------
	def hostIsValid(self, host_name):
		"""-------------------------------------------------------------------
			Function:		[hostIsValid]
			Description:	Determines if the given host name was configured
							and initialized from the user config file
			Input:			
			  [host_name]	Name of the host to validate
			Return:			True if host was configured. False otherwise
			------------------------------------------------------------------
		"""
		if host_name not in self.__hosts:
			print("Host \'%s\' was not initialized from config file!" %
				host_name)
			return False
		return True

	def seriesIsValid(self, series_abbr):
		"""-------------------------------------------------------------------
			Function:		[seriesIsValid]
			Description:	Determines if the given series name was configured
							and initialized from the user config file
			Input:			
			  [series_abbr] Abbreviated name of the series to validate
			Return:			True if series was configured. False otherwise
			------------------------------------------------------------------
		"""
		if series_abbr not in self.__series:
			print("Series \'%s\' was not initialized from config file!" %
				series_abbr)
			return False
		return True
