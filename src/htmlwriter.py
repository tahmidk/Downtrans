# -*- coding: utf-8 -*-
"""
  Author:		Tahmid Khan
  File:			[htmlwriter.py]
  Description:	This module is responsible for modifying and writing the
  				pre-processed HTML version of a given chapter translation
"""
import os 		# OS level operations
import io 		# File reading/writing
import re 		# Regex for parsing

class HtmlWriter:
	#--------------------------------------------------------------------------
	#  ctor
	#--------------------------------------------------------------------------
	def __init__(self, res_path):
		"""-------------------------------------------------------------------
			Function:		[CONSTRUCTOR]
			Description:	Reads in the skeleton.html resource file
			Input:			
			  [res_path]	Path to skeleton.html resource
			------------------------------------------------------------------
		"""
		with io.open(os.path.join(res_path), mode='r', encoding='utf8') as res:
			self.__resource = res.read()

	#--------------------------------------------------------------------------
	#  Modification functions
	#--------------------------------------------------------------------------
	def setPageTitle(self, pg_title):
		"""-------------------------------------------------------------------
			Function:		[setPageTitle]
			Description:	Inserts a page title as an html tag into the 
							given resource string
			Input:
			  [pg_title]	The page title string
			Return:			None
			------------------------------------------------------------------
		"""
		self.__resource = re.sub(r'<!--PAGE_TITLE-->', pg_title, self.__resource)

	def setChapterTitle(self, ch_title):
		"""-------------------------------------------------------------------
			Function:		[setChapterTitle]
			Description:	Inserts a chapter title as an html header into the 
							given resource string
			Input:
			  [ch_title]	The chapter title string
			Return:			None
			------------------------------------------------------------------
		"""
		self.__resource = re.sub(r'<!--CHAPTER_TITLE-->', ch_title, self.__resource)

	def insertLine(self, line):
		"""-------------------------------------------------------------------
			Function:		[insertLine]
			Description:	Inserts a line as an html paragraph into the given 
							resource string
			Input:
			  [line]		The line to add an html element for
			Return:			None
			------------------------------------------------------------------
		"""
		line_html = "<p>%s</p>\n<!--END_OF_BODY-->" % line
		self.__resource = re.sub(r'<!--END_OF_BODY-->', line_html, self.__resource)

	def insertBlankLine(self):
		"""-------------------------------------------------------------------
			Function:		[insertBlankLine]
			Description:	Convenience function to insert blank line
			Input:			None
			Return:			None
			------------------------------------------------------------------
		"""
		self.insertLine('\n')

	#--------------------------------------------------------------------------
	#  Accessor function
	#--------------------------------------------------------------------------
	def getResourceString(self):
		return self.__resource