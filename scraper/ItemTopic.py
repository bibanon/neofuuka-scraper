import time

from .ItemPost import *
from .Utils import *

class ItemTopic():
	def __init__(self):
		self.board = None
		
		self.number = None
		self.time_posted = None
		self.time_bumped = None
		self.time_modified = None
		self.time_archived = None
		self.time_deleted = None # used only to flag for removal, maybe change this?
		self.posters = None # removed from json when archived
		self.sticky = False
		self.closed = False
		self.rotate = False
		self.page = None
		
		self.posts = [] # list of ItemPostTmp
		self.index_count_reply = None # last reply count reported by catalog
		self.index_count_image = None # last image count reported by catalog
		self.last_seen_reply = None # highest post number seen in thread
		self.archive = False # was from archive.json
		self.missing = False # is gone from the index
		self.fetch_exec = False # is being fetched right now
		self.fetch_fast = False # was last fetch a catalog fetch
		self.fetch_need = None # does it need a fetch soon, timestamp
		self.fetch_last = None # when the last fetch happened (or first cat)
	
	def get_hash(self):
		return \
			get_hash_obj([
				self.number,
				self.time_posted,
				self.time_bumped,
				self.time_modified,
				self.time_archived,
				self.time_deleted,
				self.posters,
				self.sticky,
				self.closed,
				self.rotate,
			])
	
	def get_link(self):
		return (self.board.conf["sourceLinkPosts"] + "/" + self.board.get_source_name() + "/thread/" + str(self.number) + ".json")
	
	def make_from_api(self, data):
		try:
			if data["no"] < 1:
				raise Exception()
			
			if data["resto"] != 0:
				raise Exception()
			
			if data["no"] != self.number:
				raise Exception()
			
			self.time_posted = int(data["time"])
			
			if self.time_bumped == None:
				self.time_bumped = self.time_posted
			
			if data.get("sticky"): self.sticky = True
			if data.get("sticky_cap"): self.rotate = True
			
			if data.get("archived"):
				if data.get("archived_on"):
					self.time_archived = int(data["archived_on"])
				
				if not self.time_archived:
					self.time_archived = int(time.time())
			else:
				if data.get("closed"):
					self.closed = True
			
			if data.get("unique_ips"):
				if self.posters == None:
					self.posters = 0
				
				if self.posters < data["unique_ips"]:
					self.posters = data["unique_ips"]
		except:
			self.board.log(self.board, f"Failed to parse opener in topic #{self.number} [weird]")
			pass
	
	def process_post(self, post):
		if not self.board.lock.locked():
			# lock before calling this
			raise Exception()
		
		if post.number == self.number:
			# update topic from post json
			self.make_from_api(post.data)
		
		post_tmp = None
		
		for item in self.posts:
			if item.number == post.number:
				post_tmp = item
				break
		
		if post_tmp == None:
			# first time we're seeing this post
			
			post_tmp = ItemPostTmp()
			post_tmp.number = post.number
			self.posts.append(post_tmp)
			
			if post.file_time:
				# add file to fetch queue
				# TODO: for new stack
				
				'''
				if self.board.conf.get("doSaveFilesThb"):
					file = ItemFile(post, FileType1.THB)
					self.board.save_files.append(file)
				
				if self.board.conf.get("doSaveFilesSrc"):
					file = ItemFile(post, FileType1.SRC)
					self.board.save_files.append(file)
				'''
				
				pass
		
		hash = post.get_hash()
		
		if post_tmp.hash != hash:
			# this post is new or modified
			
			post_tmp.hash = hash
			
			if (
				self.time_bumped == None or
				self.time_bumped < post.time_posted
			):
				# update bump time
				self.time_bumped = post.time_posted
			
			if (
				self.last_seen_reply == None or
				self.last_seen_reply < post.number
			):
				# update last reply
				self.last_seen_reply = post.number
			
			if (
				post.time_deleted_file != None and
				post_tmp.time_deleted_file == None
			):
				# update row with deleted file
				post_tmp.time_deleted_file = post.time_deleted_file
				post_tmp.insert = True
			
			# add post to insert queue
			self.board.save_posts.append(post)
