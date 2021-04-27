import time
import json
import html
import re
import hashlib
import datetime
import pickle
import zlib
import pytz

# timezones for asagi fuckup
TIMEZONE_UTC = pytz.timezone("UTC")
TIMEZONE_4CH = pytz.timezone("America/New_York")

# get crc32 of object
def checksum(a):
	# json is somewhat slow and can't encode all types so we use pickle
	# pickle isn't guaranteed to be deterministic but it generally is here
	return zlib.crc32(pickle.dumps(a))

# encode an object into json
def json_encode_obj(a):
	return json.dumps(obj=a, separators=(",",":"))

# escape html chars, consistent with yotsuba
def asagi_html_escape(a):
	a = a.replace("&", "&amp;")
	a = a.replace("\"", "&quot;")
	a = a.replace("\'", "&#039;")
	a = a.replace("<", "&lt;")
	a = a.replace(">", "&gt;")
	return a

# parse comment html from yotsuba into asagi text
# yes, the substr checks actually speed this up significantly
def asagi_comment_parse(a):
	# literal tags
	if "[" in a:
		a = re.sub(
			"\\[(/?(spoiler|code|math|eqn|sub|sup|b|i|o|s|u|banned|info|fortune|shiftjis|sjis|qstcolor))\\]",
			"[\\1:lit]",
			a
		)
	
	# abbr, exif, oekaki
	if "\"abbr" in a: a = re.sub("((<br>){0-2})?<span class=\"abbr\">(.*?)</span>", "", a)
	if "\"exif" in a: a = re.sub("((<br>)+)?<table class=\"exif\"(.*?)</table>", "", a)
	if ">Oek" in a: a = re.sub("((<br>)+)?<small><b>Oekaki(.*?)</small>", "", a)
	
	# banned
	if "<stro" in a:
		a = re.sub("<strong style=\"color: ?red;?\">(.*?)</strong>", "[banned]\\1[/banned]", a)
	
	# fortune
	if "\"fortu" in a:
		a = re.sub(
			"<span class=\"fortune\" style=\"color:(.+?)\"><br><br><b>(.*?)</b></span>",
			"\n\n[fortune color=\"\\1\"]\\2[/fortune]",
			a
		)
	
	# code tags
	if "<pre" in a:
		a = re.sub("<pre[^>]*>", "[code]", a)
		a = a.replace("</pre>", "[/code]")
	
	# math tags
	if "\"math" in a:
		a = re.sub("<span class=\"math\">(.*?)</span>", "[math]\\1[/math]", a)
		a = re.sub("<div class=\"math\">(.*?)</div>", "[eqn]\\1[/eqn]", a)
	
	# sjis tags
	if "\"sjis" in a:
		a = re.sub("<span class=\"sjis\">(.*?)</span>", "[shiftjis]\\1[/shiftjis]", a) # use [sjis] maybe?
	
	# quotes & deadlinks
	if "<span" in a:
		a = re.sub("<span class=\"quote\">(.*?)</span>", "\\1", a)
		
		# hacky fix for deadlinks inside quotes
		for idx in range(3):
			if not "deadli" in a: break
			a = re.sub("<span class=\"(?:[^\"]*)?deadlink\">(.*?)</span>", "\\1", a)
	
	# other links
	if "<a" in a:
		a = re.sub("<a(?:[^>]*)>(.*?)</a>", "\\1", a)
	
	# spoilers
	a = a.replace("<s>", "[spoiler]")
	a = a.replace("</s>", "[/spoiler]")
	
	# newlines
	a = a.replace("<br>", "\n")
	a = a.replace("<wbr>", "")
	
	a = html.unescape(a)
	
	return a

# fuck up a timestamp in the same way asagi does
# aka convert it into America/New_York and pretend it's UTC
# probably a leftover from the old days of parsing HTML dates
def asagi_timestamp_conv(a):
	a = datetime.datetime.fromtimestamp(a, tz=TIMEZONE_UTC)
	a = a.astimezone(TIMEZONE_4CH)
	a = a.replace(tzinfo=TIMEZONE_UTC)
	a = int(a.timestamp())
	return a

# convert capcode string from yotsuba to asagi char
def asagi_capcode_conv(a):
	if a:
		if a == "mod": return "M"
		if a == "admin": return "A"
		if a == "admin_highlight": return "A"
		if a == "developer": return "D"
		if a == "verified": return "V"
		if a == "founder": return "F"
		if a == "manager": return "G"
		
		return "M"
	
	return "N"


# very basic profiling utils
# this is all I need anyway

def prof_timer():
	return time.perf_counter()

def prof_print(timer, txt="?"):
	delta = (prof_timer() - timer)
	print(f"PROFILER: {delta:.6f} in '{txt}'")
