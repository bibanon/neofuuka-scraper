import json
import time
import math

from .Thread import *
from .Requests import *
from .ItemTopic import *
from .Utils import *


def should_archive_topic(topic_d, conf):
	"""
	- If a post is blacklisted and whitelisted, it will not be archived - blacklisted filters beat whitelisted filters.
	- If only a blacklist is specified, only skip blacklisted posts and archive everything else.
	- If only a whitelist is specified, only archive whitelist posts and archive everything else.
	- If no lists are specified, archive everything.
	"""

	subject = topic_d.get('sub', False)
	comment = topic_d.get('com', False)

	blacklist_post_filter = conf.get('blacklistPostFilter', False)
	if blacklist_post_filter:
		if subject:
			if re.fullmatch(blacklist_post_filter, subject, re.IGNORECASE) is not None:
				return False
			
		if comment:
			if re.fullmatch(blacklist_post_filter, comment, re.IGNORECASE) is not None:
				return False
	
	whitelist_post_filter = conf.get('whitelistPostFilter', False)
	if whitelist_post_filter:
		if subject:
			if re.fullmatch(whitelist_post_filter, subject, re.IGNORECASE) is not None:
				return True
			
		if comment:
			if re.fullmatch(whitelist_post_filter, comment, re.IGNORECASE) is not None:
				return True
			
		return False
	
	return True
				

class Indexer(Thread):
	def __init__(self, board, **args):
		super().__init__(board, **args)
		
		self.archived_once = False # have we done at least one archive fetch since startup?
		self.archived_need = False # do we need to do an archive fetch again because last failed?
		self.conn_success_last = 0 # time of last successful index fetch
		self.conn_failure_count = 0 # number of consecutive index fetch fails
	
	def run(self):
		super().run()
		
		self.board.sleep(3)
		
		while True:
			if self.board.stop(): break
			
			if not self.board.info_has_index_live:
				self.board.sleep(0.3)
				continue
			
			self.board.log(self, "Updating topic index...")
			
			res = \
				self.board.requests.make(
					url = self.board.get_link_index_live(),
					type = RequestType.TEXT,
					since = True
				)
			
			if res.code != 200:
				if res.code == 404:
					self.board.log(self, "Index not found, board doesn't exist!?")
					self.board.sleep(60*3)
					continue
				
				if res.code == 304:
					with self.board.lock:
						self.board.log(self, f"Not Modified - {self.get_state_str()}")
					
					self.board.sleep(self.board.conf["timeBetweenIndexUpdates"])
					continue
				
				self.board.log(self, f"Index fetch failed (code {res.code})")
				self.conn_failure_count += 1
				self.board.sleep(10)
				continue
			
			# decode and validate
			try:
				data = res.data
				data = json.loads(data)
				
				if not data: raise Exception()
				if not data[0]: raise Exception()
				if not data[0]["page"]: raise Exception()
			except:
				# got a malformed response
				self.board.log(self, "Index json parse failed [weird]")
				self.board.sleep(10)
				continue
			
			self.board.lock.acquire()
			
			# hash maps for topics
			topics_in_board = {} # topics already in the board object
			topics_in_index = {} # topics we've fetched from the site
			
			# build map
			for topic in self.board.topics:
				topics_in_board[topic.number] = topic
			
			# use a consistent time
			time_now = time.time()
			
			# count modified topics
			count_mod = 0
			count_cat = 0
			
			try:
				for page_d in data:
					for topic_d in page_d["threads"]:
						try:
							if (
								type(topic_d["no"]) is not int or
								type(topic_d["last_modified"]) is not int
							):
								raise Exception()
							
							if not should_archive_topic(topic_d, self.board.conf):
								continue

							topic = None
							
							# find the corresponding topic object
							topic = topics_in_board.get(topic_d["no"])
							
							did_fast = False
							
							# create a topic object if it doesn't exist
							if topic == None:
								topic = ItemTopic()
								
								topic.board = self.board
								topic.number = topic_d["no"]
								
								# mark for immediate fetch
								topic.fetch_need = time_now
								
								self.board.topics.append(topic)
								
								if (
									"resto" in topic_d and
									topic_d.get("replies") == 0
								):
									# this topic has no replies, no need to fetch
									
									post = ItemPostFull(topic, topic_d)
									
									if post.valid:
										did_fast = True
										
										topic.process_post(post)
										
										if topic.posters == None:
											# topic with no replies obviously has 1 poster
											topic.posters = 1
										
										topic.fetch_need = None
										topic.fetch_last = time_now
								
								count_mod += 1
								count_cat += (1 if did_fast else 0)
								
								# self.board.log(self, (f"Topic #{topic.number} has appeared" + (" (cat)" if did_fast else "")))
							else:
								# it's still here
								topic.missing = False
								
								# check if modified
								
								# sometimes reply count can change without modtime changing
								# seems to happen when an ip gets all its posts wiped at once
								
								if (
									topic.time_modified != topic_d["last_modified"] or
									topic.index_count_reply != topic_d.get("replies") or
									topic.index_count_image != topic_d.get("images")
								):
									# check if we can use catalog data
									
									if(
										"resto" in topic_d and # is valid full post data
										"last_replies" in topic_d and # has a last_replies list
										isinstance(topic_d["last_replies"], list) and # is actually valid
										len(topic_d["last_replies"]) >= 1 and # contains at least one reply
										topic.last_seen_reply != None and # sanity check
										topic.index_count_reply != None and # sanity check
										topic.fetch_need == None and # not currently scheduled for a full fetch
										topic_d.get("replies", 0) > topic.index_count_reply and  # has more replies than before
										(topic_d["last_modified"] - topic.time_modified) < self.board.conf.get("catalogScrapeTimeFreq", (60*3)) # was last modified less than x secs ago
									):
										posts = []
										has_last = False
										count_new = 0
										
										# post data we might want to process
										posts_d = ([topic_d] + topic_d["last_replies"])
										
										for post_d in posts_d:
											post = ItemPostFull(topic, post_d)
											
											if post.valid:
												posts.append(post)
												
												if post.number == topic.last_seen_reply:
													has_last = True
												
												if post.number > topic.last_seen_reply:
													count_new += 1
										
										if (
											has_last and # the last seen reply is present
											count_new > 0 and # has at least 1 known new reply
											topic_d.get("replies") == (topic.index_count_reply + count_new) # reply count is as expected
										):
											did_fast = True
											
											for post in posts:
												topic.process_post(post)
											
											if not topic.fetch_fast:
												# only update fetch_last on the first consecutive catalog scrape
												# this ensures we will always do a full fetch after the time limit
												# even if catalog scrapes keep happening
												topic.fetch_last = time_now
											
											topic.fetch_need = None
											topic.fetch_fast = True
									
									if not did_fast:
										topic.fetch_fast = False
										
										if (
											topic.fetch_need == None or
											topic.fetch_need > time_now
										):
											topic.fetch_need = time_now
									
									count_mod += 1
									count_cat += (1 if did_fast else 0)
									
									# self.board.log(self, (f"Topic #{topic.number} has been modified" + (" (cat)" if did_fast else "")))
							
							# update thread values
							topic.time_modified = topic_d["last_modified"]
							topic.index_count_reply = topic_d.get("replies")
							topic.index_count_image = topic_d.get("images")
							
							# keep track of page num
							topic.page = page_d.get("page")
							
							# add to map
							topics_in_index[topic.number] = True
						except:
							# in case the json decides to go full retard
							self.board.log(self, "Index processing failed at topic level [weird]")
							pass
			except:
				# in case the json decides to go even beyond
				self.board.log(self, "Index processing failed at outer level [weird]")
				pass
			
			# decide if we should do archive index
			do_archive = None
			
			# startup archive index
			if self.board.conf.get("indexArchiveOnStartup", False):
				if not self.archived_once:
					do_archive = "startup"
			
			# downtime archive index
			if self.board.conf.get("indexArchiveOnConnect", False):
				if (
					self.conn_failure_count > 5 and
					(time.time() - self.conn_success_last) > (60*60*5)
				):
					do_archive = "downtime"
			
			# last archive index failed
			if self.archived_need:
				do_archive = "lastfailed"
			
			# actually do archive index
			if do_archive != None:
				self.board.log(self, f"Indexing archive ({do_archive})")
				
				try:
					# make request
					res = \
						self.board.requests.make(
							url = self.board.get_link_index_arch(),
							type = RequestType.TEXT
						)
					
					if res.code != 200:
						# if not found or not modified, we're done
						if res.code in [404, 304]:
							self.archived_once = True
							raise Exception()
						
						self.archived_need = True
						raise Exception()
					
					self.archived_need = False
					
					# decode and validate
					data = res.data
					data = json.loads(data)
					
					if not data: raise Exception()
					if not data[0]: raise Exception()
					
					data.sort(reverse=True)
					
					target = self.board.conf.get("indexArchivePercent", 0.50)
					target = math.ceil(len(data) * target)
					
					count_all = 0
					count_use = 0
					
					for topic_d in data:
						if type(topic_d) is not int:
							raise Exception()
						
						count_all += 1
						
						if count_all > target:
							break
						
						# ignore topics we already have
						if topics_in_board.get(topic_d): continue
						if topics_in_index.get(topic_d): continue
						
						try:
							if self.board.storage.conn:
								value = \
									self.board.storage.conn.get(
										name=self.board.storage.key(["board", self.board.get_name(), "topic", topic_d, "archived"]),
									)
								
								if value:
									continue
						except:
							pass
						
						topic = ItemTopic()
						
						topic.board = self.board
						topic.number = topic_d
						topic.time_modified = time_now
						topic.archive = True
						
						# archived topics are of lowest priority
						topic.fetch_need = (time_now + (60*60*24*3))
						
						self.board.topics.append(topic)
						
						topics_in_index[topic.number] = True
						
						count_use += 1
						
						continue
					
					self.archived_once = True
					
					self.board.log(self, f"Archive index got {count_use} topics")
				except:
					self.board.log(self, "Indexing archive failed")
					pass
			
			self.conn_success_last = time.time()
			self.conn_failure_count = 0
			
			# sort topic by number
			self.board.topics.sort(
				key = lambda topic: topic.number,
				reverse = False # newest to oldest
			)
			
			if len(topics_in_index.keys()) > 0:
				# check for missing topics and force a fetch on them
				for topic in self.board.topics:
					if not topic.number in topics_in_index:
						if not (
							topic.missing or
							topic.archive or
							topic.time_deleted or
							topic.time_archived
						):
							topic.fetch_need = (time_now + 0.01)
							topic.missing = True
							
							count_mod += 1
							
							# self.board.log(self, f"Topic #{topic.number} has disappeared")
			else:
				self.board.log(self, "Index was empty, ignoring missing topics [weird]")
			
			self.board.log(self, f"Updated - mod={count_mod - count_cat}+{count_cat} {self.get_state_str()}")
			
			self.board.lock.release()
			
			self.board.sleep(self.board.conf["timeBetweenIndexUpdates"])
			
			continue
	
	def get_state_str(self):
		return " ".join([
			f"idx={len(self.board.topics)}",
			f"ins={len(self.board.save_posts)}",
			f"img={len(self.board.save_files)}",
		])
