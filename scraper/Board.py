import time
import math
import datetime
import threading
import multiprocessing
import signal
import requests
import psutil

from .Scraper import *
from .Thread import *
from .Requests import *
from .Database import *
from .Storage import *
from .Indexer import *
from .FetcherPosts import *
from .FetcherFiles import *
from .Inserter import *
from .ItemFile import *

class Board(multiprocessing.Process):
	def __init__(self, scraper, name, conf, args):
		super().__init__()
		
		# validate name
		if re.match(r"^([a-zA-Z0-9_\-])+$", name) == None:
			raise Exception("Board name is invalid")
		
		# multiprocessing.Process stuff
		self.name = f"Scraper /{name}/"
		self.daemon = True
		
		self.name1 = name
		self.conf = conf
		self.args = args
		
		self.shared = scraper.shared
		self.master = scraper.pid
		
		# stop signal
		self.stop1 = False
		
		# threads
		self.threads = None
		
		# objects
		self.lock = None
		self.lock_log = None
		self.requests = None
		self.database = None
		self.storage = None
		
		# data
		self.topics = None # list of active topics
		self.save_posts = None # queue of posts (ItemPostFull) waiting to be inserted
		self.save_files = None # queue of files (ItemFile) waiting to be downloaded
		# self.save_hashes = None # for inserting calculated file hashes in new schema
		
		# other info
		self.info_has_index_live = False
		self.info_has_index_arch = False
		
		self.fix_config()
	
	def run(self):
		self.log(self, "Board start")
		
		if self.stop(): return
		
		# handle signals
		signal.signal(signal.SIGINT, self.signal)
		signal.signal(signal.SIGTERM, self.signal)
		
		# create objects
		self.lock = threading.Lock()
		self.lock_log = threading.Lock()
		self.requests = Requests(self)
		self.database = Database(self)
		self.storage = Storage(self)
		
		# create data
		self.topics = []
		self.save_posts = []
		self.save_files = []
		
		# create threads
		self.threads = []
		
		# object workers
		self.threads.append(WorkerData(self))
		self.threads.append(WorkerDatabase(self))
		
		# main thread indexer
		self.threads.append(Indexer(self))
		
		# database inserters
		if self.conf.get("doSavePosts", False):
			self.threads.append(Inserter(self))
		
		# post fetchers
		for idx in range(self.conf.get("threadsForPosts", 0)):
			self.threads.append(FetcherPosts(self, index=(idx+1)))
		
		# file fetchers thb
		if self.conf.get("doSaveFilesThb", False):
			for idx in range(self.conf.get("threadsForFilesThb", 0)):
				self.threads.append(FetcherFiles(self, index=(idx+1), type=FileType1.THB))
		
		# file fetchers src
		if self.conf.get("doSaveFilesSrc", False):
			for idx in range(self.conf.get("threadsForFilesSrc", 0)):
				self.threads.append(FetcherFiles(self, index=(idx+1), type=FileType1.SRC))
		
		if self.stop(): return
		
		# fetch remote info
		# maybe take out of main thread?
		self.fetch_remote_info()
		
		if self.stop(): return
		
		# start threads
		for thread in self.threads:
			thread.start()
		
		# wait for stop signal
		while True:
			if self.stop(): break
			time.sleep(0.1)
			continue
		
		self.log(None, "Stopping...")
		
		# wait for threads to stop
		while True:
			wait = False
			
			for thread in self.threads:
				if thread.is_alive():
					wait = True
					break
			
			if not wait: break
			
			time.sleep(0.1)
			
			continue
		
		self.log(None, "Stopped")
		
		return
	
	def stop(self):
		if self.shared.stop.value != 0: return True
		if self.stop1: return True
		return False
	
	def signal(self, signum, frame):
		self.stop1 = True
	
	def schema(self):
		return Schema.ASAGI
	
	def log(self, source = None, text = "?"):
		date_now = datetime.datetime.now()
		date_now = date_now.strftime("%y-%m-%d %H:%M:%S")
		
		if source == None: source = self
		
		source_name = f"/{self.get_name()}/ {source.__class__.__name__}"
		if isinstance(source, Thread): source_name = source.name
		
		# if "DBG " in text: return
		# if isinstance(source, FetcherPosts): return
		
		msg = f"{date_now} {source_name} - {text}" # •
		
		print(msg)
		
		'''
		with self.lock_log:
			file = open(f"./scraper.log.{self.get_name()}.txt", "a", encoding="utf8")
			file.write(msg + "\n")
			file.close()
		'''
	
	def sleep(self, value = 1.0):
		while True:
			if self.stop(): break
			if value <= 0: break
			
			tmp = min(value, 0.1)
			
			time.sleep(tmp)
			
			value = (value - tmp)
			
			if value < 0.001: value = 0
			
			continue
	
	def fix_config(self):
		if not self.conf.get("sourceFormat"):
			self.conf["sourceFormat"] = "yotsuba"
		
		if not self.conf.get("requestUserAgent", None):
			self.conf["requestUserAgent"] = "it is a mystery"
		
		if self.conf.get("sourceLinkPosts") and not self.conf.get("sourceLinkFilesThb"): self.conf["sourceLinkFilesThb"] = self.conf.get("sourceLinkPosts")
		if self.conf.get("sourceLinkPosts") and not self.conf.get("sourceLinkFilesSrc"): self.conf["sourceLinkFilesSrc"] = self.conf.get("sourceLinkPosts")
		if self.conf.get("sourceLinkFilesThb") and not self.conf["sourceLinkPosts"]: self.conf["sourceLinkPosts"] = self.conf.get("sourceLinkFilesThb")
		if self.conf.get("sourceLinkFilesSrc") and not self.conf["sourceLinkPosts"]: self.conf["sourceLinkPosts"] = self.conf.get("sourceLinkFilesSrc")
		
		if not self.conf.get("sourceLinkPosts"): self.conf["sourceLinkPosts"] = "https://a.4cdn.org"
		if not self.conf.get("sourceLinkFilesThb"): self.conf["sourceLinkFilesThb"] = "https://i.4cdn.org"
		if not self.conf.get("sourceLinkFilesSrc"): self.conf["sourceLinkFilesSrc"] = "https://i.4cdn.org"
		if not self.conf.get("fileSavePath"): self.conf["fileSavePath"] = "./media/"
		
		self.conf["sourceLinkPosts"] = self.conf["sourceLinkPosts"].rstrip("/\\")
		self.conf["sourceLinkFilesThb"] = self.conf["sourceLinkFilesThb"].rstrip("/\\")
		self.conf["sourceLinkFilesSrc"] = self.conf["sourceLinkFilesSrc"].rstrip("/\\")
		
		self.conf["threadsForPosts"] = min(self.conf.get("threadsForPosts", 0), 5)
		self.conf["threadsForFilesThb"] = min(self.conf.get("threadsForFilesThb", 0), 10)
		self.conf["threadsForFilesSrc"] = min(self.conf.get("threadsForFilesSrc", 0), 10)
		
		self.conf["timeBetweenIndexUpdates"] = max(self.conf.get("timeBetweenIndexUpdates", 15), 5)
		self.conf["timeBetweenTopicForceUpdates"] = max(self.conf.get("timeBetweenTopicForceUpdates", 1200), 600)
		
		self.conf["requestThrottleBoard"] = self.conf.get("requestThrottleBoard", 0.0)
		self.conf["requestThrottleGlobal"] = self.conf.get("requestThrottleGlobal", 0.0)
	
	def fetch_remote_info(self):
		for _ in range(3):
			if self.stop(): break
			
			try:
				res = \
					requests.request(
							url = self.get_link_index_live(),
							method = "head",
							timeout = 10.0,
							headers = {
								"User-Agent": self.conf.get("requestUserAgent")
							}
						)
				
				if res.status_code == 200:
					self.info_has_index_live = True
					break
				
				if res.status_code == 404:
					self.info_has_index_live = False
					break
			except:
				pass
		
		for _ in range(3):
			if self.stop(): break
			
			try:
				res = \
					requests.request(
							url = self.get_link_index_arch(),
							method = "head",
							timeout = 10.0,
							headers = {
								"User-Agent": self.conf.get("requestUserAgent")
							}
						)
				
				if res.status_code == 200:
					self.info_has_index_arch = True
					break
				
				if res.status_code == 404:
					self.info_has_index_arch = False
					break
			except:
				pass
		
		self.log(self, ("Remote has index live? " + str(self.info_has_index_live)))
		self.log(self, ("Remote has index arch? " + str(self.info_has_index_arch)))
	
	def get_name(self):
		return self.name1
	
	def get_name_src(self):
		return (self.conf.get("sourceBoard") if self.conf.get("sourceBoard") else self.get_name())
	
	def get_link_base(self):
		return (self.conf.get("sourceLinkPosts") + "/" + self.get_name_src())
	
	def get_link_index_live(self):
		return (
			self.get_link_base() + "/" +
			("catalog" if self.conf.get("catalogScrapeEnable", False) else "threads") + ".json"
		)
	
	def get_link_index_arch(self):
		return (self.get_link_base() + "/archive.json")

class WorkerData(Thread):
	def run(self):
		super().run()
		
		timer_info = time.time()
		timer_limit = time.time()
		
		self.board.sleep(3.0)
		
		while True:
			# check master process status
			try:
				psutil.Process(self.board.master)
			except psutil.NoSuchProcess:
				self.board.log(None, "Master process died!")
				self.board.stop1 = True
			except:
				self.board.log(None, "Unknown error when checking master process [weird]")
			
			if self.board.stop(): break
			
			time_now = time.time()
			
			if (time_now - timer_info) > (60*10):
				timer_info = time_now
				
				self.board.log(self.board, "Updating remote info")
				
				self.board.fetch_remote_info()
			
			if (time_now - timer_limit) > (60*20):
				timer_limit = time_now
				
				self.board.log(self.board, "Applying queue limits")
				
				with self.board.lock:
					# these numbers should never happen
					self.board.topics = self.board.topics[-30000:]
					self.board.save_posts = self.board.save_posts[-200000:]
					self.board.save_files = self.board.save_files[-200000:]
			
			self.board.sleep(1.0)
			
			continue

class WorkerDatabase(Thread):
	def run(self):
		super().run()
		
		while True:
			if self.board.stop():
				if self.board.database.conn:
					self.board.database.lock.acquire()
				
				self.board.database.disconnect()
				
				break
			
			if self.board.database.conn == None:
				self.board.database.connect()
			
			try:
				if (
					self.board.database.act_start(True, 3.0)
				):
					self.board.database.conn.ping()
					self.board.database.act_finish()
			except Exception as err:
				self.board.database.error(err)
			
			self.board.sleep(10.0)
			
			continue

class WorkerTest(Thread):
	def run(self):
		super().run()
		
		self.board.sleep(1.0)
		
		while True:
			if self.board.stop(): break
			
			# example usage of database
			# lock is intentionally not released if error occurs
			# to stop other threads from trying to use an bad conn
			# the database.error() function will handle any issues
			
			'''
			try:
				self.board.database.lock.acquire()
				
				self.board.log(self, "show tables")
				
				cursor = self.board.database.cursor()
				cursor.execute("SHOW TABLES")
				
				self.board.database.lock.release()
			except Exception as err:
				self.board.database.error(err)
				pass
			'''
			
			self.board.sleep(3.0)
			
			continue
