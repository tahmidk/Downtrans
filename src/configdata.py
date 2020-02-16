# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[configdata.py]
  Description:	This module initializes and holds data contained
  				in a given config JSON file customized by the user
"""
import json

# Length of dividers when printing
DIVIDER_BOLD = "=" * 90
DIVIDER_THIN = "-" * 90

class ConfigData:
	#--------------------------------------------------------------------------
	#  ctor
	#--------------------------------------------------------------------------
	def __init__(self, config_path):
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

			# Initialize preferred browser path and counters
			self.browser = config['preferredBrowser']
			self.num_hosts = len(config['hosts'])
			self.num_series = len(config['series'])

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
		self.hosts = {}
		print(DIVIDER_BOLD)
		print("Detected Host Websites:")
		print(DIVIDER_THIN)
		for entry in hosts:
			self.hosts[entry['host_name']] = entry['base_url']
			self.num_hosts += 1
			print("\t%-20s: %s" % (entry['host_name'], entry['base_url']))
		print(DIVIDER_BOLD)

	def initSeriesMap(self, series):
		"""-------------------------------------------------------------------
			Function:		[initSeriesMap]
			Description:	Initializes this container's series map
			Input:			
			  [series]		JSON unpacked list of series
			Return:			None
			------------------------------------------------------------------
		"""
		self.series = {}
		print(DIVIDER_BOLD)
		print("Detected Series Data:")
		print(DIVIDER_THIN)
		for entry in series:
			self.series[entry['name']] = {
				'lang': entry['lang'],
				'host': entry['host'],
				'code': entry['code']
			}
			print("\t%-20s: lang=%-5s code=%-10s host=%s" % (
					entry['name'],
					entry['lang'],
					entry['host'],
					entry['code']
				)
			)
		print(DIVIDER_BOLD)

	#--------------------------------------------------------------------------
	#  Accessor functions
	#--------------------------------------------------------------------------
	def getNumHosts(self):
		"""-------------------------------------------------------------------
			Function:		[getNumHosts]
			Description:	Fetches the number of user provided hosts
			Input:			None
			Return:			Number of hosts
			------------------------------------------------------------------
		"""
		return self.num_hosts

	def getNumSeries(self):
		"""-------------------------------------------------------------------
			Function:		[getNumHosts]
			Description:	Fetches the number of user provided series
			Input:			None
			Return:			Number of series
			------------------------------------------------------------------
		"""
		return self.num_series

	def getPreferredBrowser(self):
		"""-------------------------------------------------------------------
			Function:		[getPreferredBrowser]
			Description:	Fetches the user provided preferred browser path
			Input:			None
			Return:			Preferred browser local absolute path
			------------------------------------------------------------------
		"""
		return self.browser

	def getSeriesLang(self, series_name):
		"""-------------------------------------------------------------------
			Function:		[getSeriesLang]
			Description:	Fetches the given series language
			Input:			
			  [series_name] Name of the series to look up
			Return:			Given series language in string form
			------------------------------------------------------------------
		"""
		if self.seriesIsValid(series_name):
			return self.series[series_name]['lang']
		return None

	def getSeriesHost(self, series_name):
		"""-------------------------------------------------------------------
			Function:		[getSeriesHost]
			Description:	Fetches the given series language
			Input:			
			  [series_name]	Name of the series to look up
			Return:			Given series host website in string form
			------------------------------------------------------------------
		"""
		if self.seriesIsValid(series_name):
			return self.series[series_name]['host']
		return None

	def getSeriesCode(self, series_name):
		"""-------------------------------------------------------------------
			Function:		[getSeriesCode]
			Description:	Fetches the given series language
			Input:			
			  [series_name] Name of the series to look up
			Return:			Given series web code in string form
			------------------------------------------------------------------
		"""
		if self.seriesIsValid(series_name):
			return self.series[series_name]['code']
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
			return self.hosts[host_name]

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
		if host_name not in self.hosts:
			print("Host \'%s\' was not initialized from config file!" %
				host_name)
			return False
		return True

	def seriesIsValid(self, series_name):
		"""-------------------------------------------------------------------
			Function:		[seriesIsValid]
			Description:	Determines if the given series name was configured
							and initialized from the user config file
			Input:			
			  [series_name] Name of the series to validate
			Return:			True if series was configured. False otherwise
			------------------------------------------------------------------
		"""
		if series_name not in self.series:
			print("Series \'%s\' was not initialized from config file!" %
				series_name)
			return False
		return True
