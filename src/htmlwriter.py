# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[htmlwriter.py]
  Description:	This module is responsible for modifying and writing the
  				pre-processed HTML version of a given chapter translation
"""
import pykakasi as pkk 	# Python Japanese romanization api
import os 				# OS level operations
import io 				# File reading/writing
import re 				# Regex for parsing

class HtmlWriter:
	#--------------------------------------------------------------------------
	#  ctor
	#--------------------------------------------------------------------------
	def __init__(self, dictionary, log_file, res_path, dev_opt=False):
		"""-------------------------------------------------------------------
			Function:		[CONSTRUCTOR]
			Description:	Reads in the skeleton.html resource file
			Input:			
			  [dictionary]	Series dictionary
			  [log_file]	File descriptor to write translation logs to
			  [res_path]	Path to skeleton.html resource
			  [dev_opt] 	Output developer version HTML?
			------------------------------------------------------------------
		"""
		self.__pId = 1
		self.__linenum = 1
		self.__dictionary = dictionary
		self.__log = log_file
		with io.open(os.path.join(res_path), mode='r', encoding='utf8') as res:
			self.__resource = res.read()
			if dev_opt:
				pattern = re.compile(r"<!--PROD_LINKS-->(.*)<!--SKNIL_DORP-->", re.S)
				self.__resource = pattern.sub('', self.__resource)
			else:
				pattern = re.compile(r"<!--DEV_LINKS-->(.*)<!--SKNIL_VED-->", re.S)
				self.__resource = pattern.sub('', self.__resource)

	#--------------------------------------------------------------------------
	#  Romanization generation
	#--------------------------------------------------------------------------
	def romanizeLine(self, text_src):
		"""-------------------------------------------------------------------
			Function:		[romanizeLine]
			Description:	Generate html element for the romanization of the
							provided text (JP only)
			Input:
			  [text_src]	The source Japanese text to romanize
			Return:			string representing the HTML element with the 
							romanization
			------------------------------------------------------------------
		"""
		romanizer = pkk.kakasi()
		romanizer.setMode("H","a") 			# Enable Hiragana to ascii
		romanizer.setMode("K","a") 			# Enable Katakana to ascii
		romanizer.setMode("J","a") 			# Enable Japanese to ascii
		romanizer.setMode("r","Hepburn") 	# Use Hepburn Roman table
		romanizer.setMode("s", True) 		# Add spaces
		romanizer.setMode("C", True) 		# Capitalize

		converter = romanizer.getConverter()
		return converter.do(text_src)


	#--------------------------------------------------------------------------
	#  Modification functions
	#--------------------------------------------------------------------------
	def setPageTitle(self, series, ch):
		"""-------------------------------------------------------------------
			Function:		[setPageTitle]
			Description:	Inserts a page title as an html tag into the 
							given resource string
			Input:
			  [series]		Series name
			  [ch]			Chapter number
			Return:			None
			------------------------------------------------------------------
		"""
		pg_title = "%s %d" % (series, ch)
		self.__resource = re.sub(r'<!--PAGE_TITLE-->', pg_title, self.__resource)
		self.__log.write("Set page title: %s" % pg_title)

	def setChapterTitle(self, ch_title):
		"""-------------------------------------------------------------------
			Function:		[setChapterTitle]
			Description:	Inserts a chapter title as an html header into the 
							resource string
			Input:
			  [ch_title]	The chapter title string
			Return:			None
			------------------------------------------------------------------
		"""
		self.__resource = re.sub(r'<!--CHAPTER_TITLE-->', ch_title, self.__resource)
		self.__log.write("Set series title: %s" % ch_title)

	def setSeriesLink(self, link):
		"""-------------------------------------------------------------------
			Function:		[setSeriesLink]
			Description:	Sets the link that takes user to the webpage from 
							which the raws for this series was pulled from
			Input:
			  [link]		The HTML link to insert
			Return:			None
			------------------------------------------------------------------
		"""
		self.__resource = re.sub(r'<!--SERIES_LINK-->', link, self.__resource)
		self.__log.write("Set series link: %s" % link)

	def setChapterLink(self, link):
		"""-------------------------------------------------------------------
			Function:		[setChapterLink]
			Description:	Sets the link that takes user to the webpage from 
							which the raw for this chapter was pulled from
			Input:
			  [link]		The HTML link to insert
			Return:			None
			------------------------------------------------------------------
		"""
		self.__resource = re.sub(r'<!--CHAPTER_LINK-->', link, self.__resource)
		self.__log.write("Set chapter link: %s" % link)

	def setChapterNumber(self, ch_num):
		"""-------------------------------------------------------------------
			Function:		[setChapterNumber]
			Description:	Inserts the chapter number as an html header into
							the resource string
			Input:
			  [ch_num]		The chapter number as a string
			Return:			None
			------------------------------------------------------------------
		"""
		ch_num = "Chapter " + ch_num
		self.__resource = re.sub(r'<!--CHAPTER_NUMBER-->', ch_num, self.__resource)
		self.__log.write("Set chapter subtitle: %s" % ch_num)		

	def insertLine(self, line, lang):
		"""-------------------------------------------------------------------
			Function:		[insertLine]
			Description:	Inserts a line as an html paragraph into the given 
							resource string
			Input:
			  [line]		The line to add an html element for
			  [lang]		The language the line is in
			Return:			None
			------------------------------------------------------------------
		"""
		# Strip unnecessary white space at the beginning
		line = line.lstrip()

		# Display roma for JP
		if lang == "JP":
			raw_line = "<p class=\"content_raw notranslate\" id=r%s>%s</p>" % \
				(self.__linenum, self.romanizeLine(line))
			src_lang = "ja"
		# Display raw for CN
		elif lang == "CN":
			raw_line = "<p class=\"content_raw notranslate\" id=r%s>%s</p>" % \
				(self.__linenum, line)
			src_lang = "zh-CN"

		raw_html = "<a href=\"https://translate.google.com/?hl=en&tab=TT&authuser\
=0#view=home&op=translate&sl=%s&tl=en&text=%s\" class=\"noDecoration\
\" target=\"_blank\">%s</a>" % \
			(src_lang, line, raw_line)

		# Preprocess line using dictionary entities
		for entry in self.__dictionary:
			if entry in line:
				self.__log.write("\n\tDetected token %s in line. Replacing \
					with %s" % (entry, self.__dictionary[entry]))

				placeholder = "<span class=\"placeholder\" id=%d>placeholder\
					</span>" % self.__pId
				new_entry = "<span class=\"notranslate word_mem\" id=w%d>%s\
					</span>" % (self.__pId, self.__dictionary[entry])
				line = line.replace(entry, "%s%s" % (new_entry, placeholder))

				self.__pId += 1

		# Integrate line into resource string
		line_html = "<p class=\"content_line\" id=l%s>%s</p>" % (self.__linenum, line)
		final_html = line_html + raw_html + "\n<!--END_OF_BODY-->"
		self.__resource = re.sub(r'<!--END_OF_BODY-->', final_html, self.__resource)
		self.__linenum += 1

	def insertBlankLine(self):
		"""-------------------------------------------------------------------
			Function:		[insertBlankLine]
			Description:	Convenience function to insert blank line
			Input:			None
			Return:			None
			------------------------------------------------------------------
		"""
		line_html = "<p>\n</p>\n<!--END_OF_BODY-->"
		self.__resource = re.sub(r'<!--END_OF_BODY-->', line_html, self.__resource)

	#--------------------------------------------------------------------------
	#  Accessor function
	#--------------------------------------------------------------------------
	def getResourceString(self):
		return self.__resource