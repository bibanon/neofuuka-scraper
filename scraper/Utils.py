import time
import json
import html
import re
import hashlib
import datetime
import pytz

# timezones for asagi fuckup
TIMEZONE_UTC = pytz.timezone("UTC")
TIMEZONE_4CH = pytz.timezone("America/New_York")

# encode an object into json
def json_encode_obj(x):
	return json.dumps(obj=x, separators=(",",":"))

# generate a 4-byte hash of a string
def get_hash_str(x):
	hash = hashlib.md5()
	hash.update(x.encode("utf8"))
	return hash.digest()[0:4]

# generate a 4-byte hash of a json-able object
def get_hash_obj(x):
	return get_hash_str(json_encode_obj(x))

# escape html chars, consistent with yotsuba
def asagi_html_escape(x):
	if x:
		x = x.replace("&", "&amp;")
		x = x.replace("\"", "&quot;")
		x = x.replace("\'", "&#039;")
		x = x.replace("<", "&lt;")
		x = x.replace(">", "&gt;")
	
	return x

# parse comment html from yotsuba into asagi text
# yes, the substr checks actually speed this up significantly
def asagi_comment_parse(x):
	if x:
		# literal tags
		if "[" in x:
			x = re.sub(
				"\\[(/?(spoiler|code|math|eqn|sub|sup|b|i|o|s|u|banned|info|fortune|shiftjis|sjis|qstcolor))\\]",
				"[\\1:lit]",
				x
			)
		
		# abbr, exif, oekaki
		if "\"abbr" in x: x = re.sub("((<br>){0-2})?<span class=\"abbr\">(.*?)</span>", "", x)
		if "\"exif" in x: x = re.sub("((<br>)+)?<table class=\"exif\"(.*?)</table>", "", x)
		if ">Oek" in x: x = re.sub("((<br>)+)?<small><b>Oekaki(.*?)</small>", "", x)
		
		# banned
		if "<stro" in x:
			x = re.sub("<strong style=\"color: ?red;?\">(.*?)</strong>", "[banned]\\1[/banned]", x)
		
		# fortune
		if "\"fortu" in x:
			x = re.sub(
				"<span class=\"fortune\" style=\"color:(.+?)\"><br><br><b>(.*?)</b></span>",
				"\n\n[fortune color=\"\\1\"]\\2[/fortune]",
				x
			)
		
		# code tags
		if "<pre" in x:
			x = re.sub("<pre[^>]*>", "[code]", x)
			x = x.replace("</pre>", "[/code]")
		
		# math tags
		if "\"math" in x:
			x = re.sub("<span class=\"math\">(.*?)</span>", "[math]\\1[/math]", x)
			x = re.sub("<div class=\"math\">(.*?)</div>", "[eqn]\\1[/eqn]", x)
		
		# sjis tags
		if "\"sjis" in x:
			x = re.sub("<span class=\"sjis\">(.*?)</span>", "[shiftjis]\\1[/shiftjis]", x) # use [sjis] maybe?
		
		# quotes & deadlinks
		if "<span" in x:
			x = re.sub("<span class=\"quote\">(.*?)</span>", "\\1", x)
			
			# hacky fix for deadlinks inside quotes
			for idx in range(3):
				if not "deadli" in x: break
				x = re.sub("<span class=\"(?:[^\"]*)?deadlink\">(.*?)</span>", "\\1", x)
		
		# other links
		if "<a" in x:
			x = re.sub("<a(?:[^>]*)>(.*?)</a>", "\\1", x)
		
		# spoilers
		x = x.replace("<s>", "[spoiler]")
		x = x.replace("</s>", "[/spoiler]")
		
		# newlines
		x = x.replace("<br>", "\n")
		x = x.replace("<wbr>", "")
		
		x = html.unescape(x)
	
	return x

# fuck up a timestamp in the same way asagi does
# aka interpret it as America/New_York and convert to UTC
# probably a leftover from the days of parsing HTML dates
def asagi_timestamp_conv(x):
	x = datetime.datetime.utcfromtimestamp(x)
	x = x.astimezone(TIMEZONE_4CH)
	x = x.replace(tzinfo=TIMEZONE_UTC)
	x = int(x.timestamp())
	return x

# convert capcode string from yotsuba to asagi char
def asagi_capcode_conv(x):
	if x:
		if x == "mod": return "M"
		if x == "admin": return "A"
		if x == "admin_highlight": return "A"
		if x == "developer": return "D"
		if x == "verified": return "V"
		if x == "founder": return "F"
		if x == "manager": return "G"
		
		return "M"
	
	return "N"


# very basic profiling utils
# this is all I need anyway

def prof_timer():
	return time.perf_counter()

def prof_print(timer, txt="?"):
	delta = (prof_timer() - timer)
	print(f"PROFILER: {delta:.6f} ({txt})")
