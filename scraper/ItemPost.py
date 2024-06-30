import time
import html
import base64
import re

from .ItemFile import *
from .Utils import *

class ItemPostFull():
	# this is a full post with all data that is only kept in the insert queue
	
	def __init__(self, topic = None, data = None):
		self.board = None
		self.topic = None
		
		self.data = None # raw json data
		self.valid = False # was successfully parsed from json
		
		self.number = None
		self.time_posted = None
		self.time_deleted_post = None # not used, see cache instead
		self.time_deleted_file = None # should this be a bool?
		self.poster_name = None
		self.poster_trip = None
		self.poster_capcode = None
		self.poster_country = None
		self.poster_userid = None # removed from json when archived
		self.subject = None
		self.comment = None # kept as original html
		self.spoiler = False # independent of file
		self.file_time = None
		self.file_hash = None
		self.file_name = None
		self.file_type = None
		self.file_size = None
		self.file_dims_src = None
		self.file_dims_thb = None
		
		if topic:
			self.topic = topic
			self.board = topic.board
		
		if data:
			self.make_from_api(data)
	
	# generate small post hash
	# used to check if a post has been modified
	# no need to include fields that never change
	def get_hash(self):
		return \
			checksum([
				self.number,
				self.time_posted,
				self.time_deleted_post,
				self.time_deleted_file,
				self.poster_name,
				self.poster_trip,
				self.poster_capcode,
				self.subject,
				self.comment,
				self.spoiler, # jannies can change this!
				self.file_time,
				self.file_name,
				
				# trigger op insert if topic changes
				(
					self.topic.get_hash()
					if self.is_opener() else
					None
				)
			])
	
	def make_from_api(self, data):
		self.data = data
		self.valid = False
		
		try:
			self.number = int(data["no"])
			self.time_posted = int(data["time"])
			
			if self.number < 1:
				# something's wrong with the number
				raise Exception()
			
			if self.time_posted < 946684800:
				# something's wrong with the timestamp
				raise Exception()
			
			if (
				data["resto"] != 0 and
				data["resto"] != self.topic.number
			):
				# weird, doesn't belong to this topic
				raise Exception()
			
			if (
				data["resto"] == 0 and
				self.number != self.topic.number
			):
				# weird, is an opener but different number
				raise Exception()
			
			if data.get("name"): self.poster_name = html.unescape(data["name"])
			if data.get("trip"): self.poster_trip = data["trip"]
			if data.get("capcode"): self.poster_capcode = data["capcode"]
			if data.get("country"): self.poster_country = data["country"]
			if data.get("id"): self.poster_userid = data["id"]
			
			if data.get("sub"): self.subject = html.unescape(data["sub"])
			if data.get("com"): self.comment = data["com"]
			
			# independent of file!
			# if you submit a post with "spoiler" checkbox ticked
			# and without a file, it will still be marked spoiler
			if data.get("spoiler"):
				self.spoiler = True
			
			if data.get("ext") != None:
				self.file_time = int(data["tim"])
				self.file_hash = base64.b64decode(data["md5"])
				self.file_name = html.unescape(data["filename"])
				self.file_type = data["ext"].replace(".", "")
				self.file_size = int(data["fsize"])
				self.file_dims_src = (int(data["w"]), int(data["h"]))
				self.file_dims_thb = (int(data["tn_w"]), int(data["tn_h"]))
			
			if data.get("filedeleted"):
				self.time_deleted_file = int(time.time())
			
			self.valid = True
		except:
			self.board.log(self.board, f"Failed to parse post in #{self.topic.number} [weird]")
			pass
	
	# is this an OP post?
	def is_opener(self):
		return (self.number == self.topic.number)
	
	# generate the 'exif' asagi field for extra data
	# dont store this if thread is archived, ips are lost
	def get_extra(self):
		out = {}
		
		if self.file_time != self.get_file_time_db():
			out["tim"] = self.file_time
		
		if self.number == self.topic.number:
			if self.topic.posters != None:
				out["uniqueIps"] = str(self.topic.posters)
		
		if self.data:
			if self.data.get("board_flag"):
				out["troll_country_code"] = self.data.get("board_flag")
				out["troll_country_name"] = self.data.get("flag_name")
			
			# old board flag format, remove later
			if self.data.get("troll_country"):
				out["troll_country_code"] = self.data.get("troll_country")
				out["troll_country_name"] = self.data.get("country_name")
			
			if self.data.get("since4pass"):
				out["since4pass"] = str(self.data["since4pass"])
		
		if self.comment:
			# if the comment includes stuff that can't be normally parsed,
			# just save the whole thing so the data isn't lost or mangled
			
			if (
				self.poster_capcode or
				"<table class=\"exif" in self.comment or
				"<small><b>Oekaki" in self.comment or
				"<img " in self.comment or
				"<iframe " in self.comment or
				"src=\"" in self.comment or
				"width=\"" in self.comment or
				(
					"style=\"" in self.comment and
					not (
						"<strong style=" in self.comment or
						"class=\"fortune" in self.comment
					)
				)
			):
				out["comment"] = self.comment
		
		if len(out) > 0:
			return out
		
		return None
	
	def get_file_hash_b64(self):
		if self.file_hash:
			return base64.b64encode(self.file_hash).decode("ascii")
		
		return None
	
	def get_file_time_db(self):
		if (
			self.file_time > 1000000000000000 and
			self.board.conf.get("fileUseShortNames")
		):
			return int(self.file_time / 1000)
		
		return self.file_time
	
	def get_comment_clean(self):
		com = self.comment
		
		if com:
			if "<" in com:
				if "quotelink" in com:
					# clean quotelinks alive
					com = re.sub("<a href=\"(?:[^\"]+?)\" class=\"quotelink\"(?: target=\"_blank\")?>(&gt;(?:.+?))<\/a>", "<a>\\1</a>", com)
				
				if "deadlink" in com:
					# clean quotelinks dead
					com = re.sub("<span class=\"deadlink\">(.*?)</span>", "<a>\\1</a>", com)
				
				if "<a " in com:
					# remove misc linkification
					com = re.sub("<a href=\"(?:[^\"]+?)\" target=\"_blank\">(.*?)<\/a>", "\\1", com)
				
				'''
					if "<a " in com:
						com = re.sub("<a href=\"(?:.+?)\" class=\"quotelink\">(&gt;(?:.+?))<\/a>", "<x-link>\\1</x-link>", com)
					
					if "<span " in com:
						com = re.sub("<span class=\"deadlink\">(.*?)</span>", "<x-link>\\1</x-link>", com)
						com = re.sub("<span class=\"quote\">(&gt;(?:.*?))<\/span>(?=$|<)", "<x-quote>\\1</x-quote>", com)
					
					if "<s>" in com:
						com = com.replace("<s>", "<x-spoiler>")
						com = com.replace("</s>", "</x-spoiler>")
					
					if "<stro" in com:
						com = re.sub("<strong style=\"color: ?red;?\">(.*?)</strong>", "<x-banned>\\1</x-banned>", com)
				'''
		
		return com

class ItemPostCache():
	# this is a post cache obj that is always kept in memory, to keep track of changes
	# there will be tens of thousands of these in memory at all times, so it must be small
	
	__slots__ = [
		"number",
		"topic",
		"hash",
		"time_deleted_post",
		"time_deleted_file",
		"insert",
	]
	
	def __init__(self, post):
		self.number = post.number
		self.topic = post.topic
		
		self.hash = None
		
		self.time_deleted_post = None
		self.time_deleted_file = None
		
		self.insert = False
	
	def set_insert(self):
		self.insert = True
		self.topic.posts_ins = True
