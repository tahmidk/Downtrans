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
import bs4 as soup 						# Python HTML query tool
import re 								# Regex for personalized parsing HTML

def createParser(host):
	"""-------------------------------------------------------------------
		Function:		[createParser]
		Description:	Given a host name, creates and returns the 
						appropriate HtmlParser
		Input:
		  [host]		Host to create parser for
		Return:			Concrete HtmlParser-derived object
		-------------------------------------------------------------------
	"""
	if host == "Syosetu":
		return SyosetuParser()
	elif host == "Biquyun":
		return BiquyunParser()
	elif host == "69shu":
		return Shu69Parser()

	return None
		

#==========================================================================
#	[HtmlParser]
#	Generic abstract super class requiring children to implement a 
#	parseTitle and parseContent method. All parsers MUST inherit from
# 	this class.
#==========================================================================
class HtmlParser(ABC):
	def __init__(self, table_needed):
		# Is a page table needed for this parser
		self.table_needed = table_needed

	def needsPageTable(self):
		return self.table_needed

	"""-------------------------------------------------------------------
		Function:		[parseTitle]
		Description:	Parses the title from the HTML source code
		Input:
		  [html]		The HTML source code in string form	for a given chap
		Return:			The string representing the chapter title
		-------------------------------------------------------------------
	"""
	@abstractmethod
	def parseTitle(self, html):	pass

	"""-------------------------------------------------------------------
		Function:		[parseContent]
		Description:	Parses the chapter content from the HTML source code
		Input:
		  [html]		The HTML source code in string form	for a given chap	
		Return:			A list constisting of each line of content from the 
						chapter
		-------------------------------------------------------------------
	"""
	@abstractmethod
	def parseContent(self, html): pass

	"""-------------------------------------------------------------------
		Function:		[parsePageTableFromWeb]
		Description:	Parses out codes corresponding to all chapters in the
						given HTML table of contents from the series index 
						webpage
		Input:
		  [html]		The HTML source code in string form	of the table of 
		  				contents for a given series
		Return:			A list where the string at index i represents the url
						chapter code of the (i+1)th chapter of this series

		Note: 	Not required by all parsers. Only if chapters of the series 
				have chapter codes in the URL that DOES NOT monotonically 
				increment by 1 from one chapter to the next
		-------------------------------------------------------------------
	"""
	@abstractmethod
	def parsePageTableFromWeb(self, html): pass

	"""-------------------------------------------------------------------
		Function:		[getLatestChapter]
		Description:	Retrieves the latest chapter number for the given series
		Input:
		  [html]		The base table of contents html for a given series
		Return:			A list constisting of each line of content from the 
						chapter
		-------------------------------------------------------------------
	"""
	@abstractmethod
	def getLatestChapter(self, html): pass

#==========================================================================
#	[SyosetuParser]
#	HtmlParser specialized for parsing html chapters taken from the 
#	https://ncode.syosetu.com domain 
#==========================================================================
class SyosetuParser(HtmlParser):
	def __init__(self):
		# Page table not needed for Syosetu domain
		super(SyosetuParser, self).__init__(False)

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
			if re.fullmatch(r'\s*<br\s*/>\s*', line):
				content.append('\n')
			else:
				# Filter out <ruby> tags that are commonly found in line
				if "<ruby>" in line:
					line = re.sub(r'<ruby>(.*?)<rb>(.*?)</rb>(.*?)</ruby>', 
						r'\2', line)
				content.append(line)
			content.append('\n')

		return content

	# Syosetu domain has chapter codes corresponding to the chapter number
	#   https://ncode.syosetu.com/<ncode>/1 = Chapter 1
	#   https://ncode.syosetu.com/<ncode>/2 = Chapter 2
	#   ...
	# So page table is not needed
	def parsePageTableFromWeb(self, html): 
		return None

	def getLatestChapter(self, html):
		pattern = re.compile(r"<dl class=\"novel_sublist2\">")
		latest = len(pattern.findall(html))
		return latest

#==========================================================================
#	[BiquyunParser]
#	HtmlParser specialized for parsing html chapters taken from the 
#	https://www.biquyun.com/ domain 
#==========================================================================
class BiquyunParser(HtmlParser):
	def __init__(self):
		# Page table needed for Biquyun domain
		super(BiquyunParser, self).__init__(True)

	def parseTitle(self, html):
		title = re.findall(r'<div class="bookname">\r\n\t\t\t\t\t<h1>(.*?)\
			</h1>', html)
		return title[0]

	def parseContent(self, html):
		content = []

		# Parse lines and make them readable before adding them to content
		lines = re.findall(r'&nbsp;&nbsp;&nbsp;&nbsp;(.*?)<', html)
		for line in lines:
			content.append(line)
			content.append(u'\n')

		return content

	# Erratic chapter codes, so page table needed
	def parsePageTableFromWeb(self, html):
		# Note: this parsing scheme may be outdated for the Biquyun domain
		page_table = re.findall(r'<a href="/.*?/(.*?)\.html">', html)
		return page_table

	def getLatestChapter(self, html):
		return len(self.parsePageTableFromWeb(html))

#==========================================================================
#	[Shu69Parser]
#	HtmlParser specialized for parsing html chapters taken from the 
#	https://www.69shu.org/book/ domain 
#==========================================================================
class Shu69Parser(HtmlParser):
	def __init__(self):
		# Page table needed for Biquyun domain
		super(Shu69Parser, self).__init__(True)

	def parseTitle(self, html):
		html_soup = soup.BeautifulSoup(html, 'lxml')
		title_div = html_soup.find('div', {'class': 'h1title'})
		title = title_div.h1.string if title_div.h1 is not None else "NOTITLE"
		return title

	def parseContent(self, html):
		content = []

		# Parse lines and make them readable before adding them to content
		lines = re.findall(r'&nbsp;&nbsp;&nbsp;&nbsp;(.*?)<', html)
		for line in lines:
			content.append(line)
			content.append(u'\n')

		return content

	# Erratic chapter codes, so page table needed
	def parsePageTableFromWeb(self, html):
		page_table = []

		html_soup = soup.BeautifulSoup(html, 'lxml')
		ch_list = html_soup.find('ul', {'class': 'chapterlist'})
		for ch_elem in ch_list.find_all('li', {'class': ''}):
			if ch_elem.a is not None:
				ch_html = ch_elem.a.get('href')
				page_table.append(ch_html)

		return page_table

	def getLatestChapter(self, html):
		return len(self.parsePageTableFromWeb(html))