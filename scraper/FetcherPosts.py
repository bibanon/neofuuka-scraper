import time

from .Thread import *
from .Requests import *
from .ItemTopic import *
from .ItemPost import *

class FetcherPosts(Thread):
	def run(self):
		super().run()
		
		while True:
			if self.board.stop(): break
			
			topic = None
			reason = None
			
			self.board.lock.acquire()
			
			# get the next topic to fetch
			for topic1 in self.board.topics:
				# ignore topics already being fetched
				if topic1.fetch_exec: continue
				
				# check if topic needs an update
				
				reason1 = None
				
				if (
					topic1.fetch_last != None and
					(time.time() - topic1.fetch_last) > self.board.conf.get("timeBetweenTopicForceUpdates", 36000)
				):
					# fetched a long time ago
					reason1 = "old"
				
				if (
					topic1.fetch_last != None and
					topic1.fetch_fast == True and
					(time.time() - topic1.fetch_last) > self.board.conf.get("catalogScrapeTimeWait", 600)
				):
					# got catalog'd recently
					reason1 = "cat"
				
				if (
					topic1.fetch_need != None and
					(time.time() - topic1.fetch_need) > 2.0 # wait after mod
				):
					# indexer says it changed
					reason1 = "mod"
				
				if topic1.fetch_last == None:
					# never been fetched before
					reason1 = "new"
					
					if topic1.archive:
						reason1 = "arc"
				
				if (
					topic1.time_deleted or
					topic1.time_archived
				):
					# ignore deleted topics
					reason1 = None
				
				if reason1 != None:
					if (
						topic == None or
						(
							# sorting rules
							
							(
								topic.fetch_need == None and
								topic1.fetch_need != None
							) or
							(
								topic.fetch_need != None and
								topic1.fetch_need != None and
								topic1.fetch_need < topic.fetch_need  # sort by priority
							)
						)
					):
						topic = topic1
						reason = reason1
			
			if not topic:
				self.board.lock.release()
				self.board.sleep(0.3)
				continue
			
			topic.fetch_exec = True
			topic.fetch_need = None
			topic.fetch_last = time.time()
			topic.fetch_fast = False
		
			self.board.lock.release()
			
			self.board.log(self, f"Updating topic #{topic.number} ({reason})")
			
			res = \
				self.board.requests.make(
					url = topic.get_link(),
					type = RequestType.TEXT
				)
			
			if res.code != 200:
				if res.code == 304:
					# topic has not been modified
					# currently not used
					
					with self.board.lock:
						topic.fetch_exec = False
					
					self.board.sleep(0.1)
					continue
				
				if res.code == 404:
					# topic is gone, deleted/pruned
					
					with self.board.lock:
						# mark for removal by Inserter
						topic.time_deleted = int(time.time())
						topic.fetch_exec = False
						
						# mark as deleted by janny if recently replied to
						# and board has archive or before page threshold
						
						if (
							(
								topic.time_bumped != None and
								(topic.time_bumped - time.time()) < (60*60*10)
							) and
							(
								self.board.info_has_index_arch or
								(
									topic.page != None and
									topic.page < self.board.conf.get("topicDeleteThreshold", 8)
								)
							)
						):
							self.board.log(self, f"Topic #{topic.number} has been deleted")
							
							for post in topic.posts:
								if post.number == topic.number:
									# set time deleted on topic's post_tmp
									post.time_deleted_post = topic.time_deleted
									post.insert = True
									break
						else:
							self.board.log(self, f"Topic #{topic.number} has been pruned")
					
					self.board.sleep(0.1)
					continue
				
				# something else happened, try again later
				
				self.board.log(self, f"Topic #{topic.number} fetch failed (code {res.code})")
				
				with self.board.lock:
					topic.fetch_exec = False
					topic.fetch_need = (time.time() + 60.0)
				
				self.board.sleep(3.0)
				continue
			
			# decode and validate
			
			try:
				data = res.data
				data = json.loads(data)
				
				if not data: raise Exception()
				if not data["posts"]: raise Exception()
				if not data["posts"][0]["no"]: raise Exception()
			except:
				# got malformed data
				
				self.board.log(self, f"Topic #{topic.number} json parse failed [weird]")
				
				with self.board.lock:
					topic.fetch_exec = False
					topic.fetch_need = (time.time() + 60.0)
				
				self.board.sleep(1.0)
				continue
			
			# process posts
			
			posts_dict = {}
			
			with self.board.lock:
				for post_d in data["posts"]:
					post = ItemPost(topic, post_d)
					
					if not post.valid:
						self.board.log(self, "Post object creation failed [weird]")
						continue
					
					posts_dict[post.number] = True
					
					topic.process_post(post)
					
					continue
			
			# check for deleted posts
			
			with self.board.lock:
				for post_tmp in topic.posts:
					if (
						post_tmp.time_deleted_post == None and
						not post_tmp.number in posts_dict
					):
						post_tmp.time_deleted_post = int(time.time())
						post_tmp.insert = True
			
			# topic successfully updated and still exists
			
			with self.board.lock:
				topic.fetch_exec = False
				
				if topic.time_archived and not topic.archive:
					self.board.log(self, f"Topic #{topic.number} has been archived")
				
				if (
					topic.missing and
					not (
						topic.time_deleted or
						topic.time_archived
					)
				):
					# in some cases, if a thread gets deleted/archived and a reply is posted at the same time,
					# the thread json can be left behind in an alive state despite it being gone from the index
					# we mark it as deleted here to avoid fetching it over and over for no reason
					
					self.board.log(self, f"Topic #{topic.number} has been semi-deleted")
					topic.time_deleted = int(time.time())
			
			self.board.sleep(0.1)
			continue
