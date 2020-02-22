import bs4 as soup
from urllib.request import Request, urlopen
import ssl

def fetchHTML(url, lang):
	"""-------------------------------------------------------------------
		Function:		[fetchHTML]
		Description:	Tries to prompt a response url and return the received
						HTML content as a UTF-8 decoded string
		Input:			
		  [url]			The url to make the request to
		  [lang]		The page's language, determines decoding scheme
		Return: 		The HTML content of the given website address
		------------------------------------------------------------------
	"""
	tries = 0
	while True:
		try:
			headers = { 'User-Agent' : 'Mozilla/5.0' }
			request = Request(url, None, headers)
			response = urlopen(request, context=ssl._create_unverified_context())
			break
		# Some error has occurred
		except Exception as e:
			tries += 1
			print("\n[Error] Could not get response from <%s>... Retrying \
				[tries=%d]" % (url, tries))
			time.sleep(2)
		
		if tries == 5:
			print("\n[Error] Max tries reached. No response from <%s>. Make \
				sure this URL exists" % url)
			return None

	# Read and decode the response according to series language
	source = response.read()
	if lang == "JP":
		data = source.decode('utf8')
	elif lang == "CN":
		data = source.decode('gbk')
	else:
		print("Unrecognized language option: \'%s\'" % lang)
		print("Defaulting to deciding as UTF8")
		data = source.decode('utf8')

	return data

url = "https://www.69shu.org/book/100273/32602244.html"
sauce = fetchHTML(url, "CN")

url_soup = soup.BeautifulSoup(sauce, 'lxml')
print(url_soup)

