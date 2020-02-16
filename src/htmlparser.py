# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[htmlparser.py]
  Description:	This module implements several parsers for all the 
  				individual host entries listed in the user config 
  				JSON file. Any new parser MUST inherit from HtmlParser
"""

# =========================[ Imports ]==========================
from abc import ABC, abstractmethod		# Pythonic abstract inheritance
import re 								# Regex for parsing HTML

#==========================================================================
#	[HtmlParser]
#	Generic abstract super class requiring children to implement a 
#	parseTitle and parseContent method. All parsers MUST inherit from
# 	this class.
#==========================================================================
class HtmlParser(ABC):
	"""-------------------------------------------------------------------
		Function:		[parseTitle]
		Description:	Parses the title from the html source code
		Input:
		  [html]		The HTML source code in string form		
		Return:			The string representing the chapter title
		-------------------------------------------------------------------
	"""
	@abstractmethod
	def parseTitle(self, html):	pass

	"""-------------------------------------------------------------------
		Function:		[parseContent]
		Description:	Parses the chapter content from the html source code
		Input:
		  [html]		The HTML source code in string form		
		Return:			A list constisting of each line of content from the 
						chapter
		-------------------------------------------------------------------
	"""
	@abstractmethod
	def parseContent(self, html): pass

#==========================================================================
#	[SyosetuParser]
#	HtmlParser specialized for parsing html chapters taken from the 
#	https://ncode.syosetu.com domain 
#==========================================================================
class SyosetuParser(HtmlParser):
	def parseTitle(self, html):
		title = re.findall(r'<p class="novel_subtitle">(.*?)</p>', html)
		return title[0]

	def parseContent(self, html):
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

		return content

#==========================================================================
#	[BiquyunParser]
#	HtmlParser specialized for parsing html chapters taken from the 
#	https://www.biquyun.com/ domain 
#==========================================================================
class BiquyunParser(HtmlParser):
	def parseTitle(self, html):
		pass

	def parseContent(self, html):
		pass

#==========================================================================
#	[Shu69Parser]
#	HtmlParser specialized for parsing html chapters taken from the 
#	https://www.69shu.org/book/ domain 
#==========================================================================
class Shu69Parser(HtmlParser):
	def parseTitle(self, html):
		pass

	def parseContent(self, html):
		pass