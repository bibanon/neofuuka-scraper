import time
import enum
import threading
import requests

from .Utils import *

class Requests():
	def __init__(self, board):
		self.board = board
		
		self.lock = threading.Lock()
		
		self.types = {}
		
		self.modifieds = []
		
		for type in list(RequestType):
			tmp = RequestTypeDat()
			
			if type == RequestType.TEXT:
				tmp.timeout = self.board.conf.get("requestTimeoutText", tmp.timeout)
				tmp.interval = self.board.conf.get("requestThrottleBoard")
			
			if type == RequestType.FILE:
				tmp.timeout = self.board.conf.get("requestTimeoutFile", tmp.timeout)
				tmp.interval = 0.002
			
			self.types[type] = tmp
	
	def make(self, url, type, since = False):
		res = RequestRes()
		
		with self.types[type].lock:
			if self.types[type].interval > 0.001:
				self.board.sleep(self.types[type].interval - (time.time() - self.types[type].timelast))
			
			self.types[type].timelast = time.time()
		
		if (
			type == RequestType.TEXT and
			self.board.conf.get("requestThrottleGlobal") > 0.001
		):
			self.board.scraper.request_lock.acquire()
			self.board.sleep(self.board.conf.get("requestThrottleGlobal") - (time.time() - self.board.scraper.request_time))
			self.board.scraper.request_time = time.time()
			self.board.scraper.request_lock.release()
		
		if self.board.stop: return res
		
		time_now = time.time()
		
		hash = self.get_url_hash(url)
		
		request = {
			"url": url,
			"method": "get",
			"timeout": self.types[type].timeout,
			
			"params": {},
			"headers": {}
		}
		
		request["headers"]["User-Agent"] = self.board.conf.get("requestUserAgent", "")
		
		if type == RequestType.TEXT:
			# bypass cloudflare cache with query
			request["params"]["v"] = int(time.time())
		
		if since:
			with self.lock:
				for item in self.modifieds:
					if item.hash == hash:
						request["headers"]["If-Modified-Since"] = item.time_str
						break
		
		# self.board.log(self, "Fetch " + url)
		
		try:
			response = \
				requests.request(**request)
			
			res.code = response.status_code
			
			if res.code == 200:
				if type == RequestType.TEXT:
					with self.lock:
						modified = RequestModified(hash)
						modified.time_str = response.headers.get("Last-Modified")
						modified.time_int = self.parse_time_str(modified.time_str)
						
						if modified.time_int:
							if since:
								for item in self.modifieds:
									if item.hash == hash:
										# work around an old 4chan bug where json can go back in time
										if modified.time_int < item.time_int:
											res.code = 304
										
										break
							
							if res.code == 200:
								for item in self.modifieds:
									if item.hash == hash:
										self.modifieds.remove(item)
										break
								
								self.modifieds.insert(0, modified)
								self.modifieds = self.modifieds[0:1000]
				
				if res.code == 200:
					res.data = response.content
		except:
			pass
		
		return res
	
	def get_url_hash(self, url):
		return get_hash_str(url)
	
	def parse_time_str(self, str):
		try:
			return int(time.mktime(time.strptime(str, "%a, %d %b %Y %H:%M:%S %Z")))
		except:
			pass
		
		return None

class RequestRes():
	def __init__(self):
		self.code = 0
		self.data = None
		
		self.err = None # maybe use this in case of exception and code=0

class RequestType(enum.Enum):
	TEXT = enum.auto()
	FILE = enum.auto()

class RequestTypeDat():
	def __init__(self):
		self.lock = threading.Lock()
		self.timeout = 10
		self.interval = 0.0
		self.timelast = 0.0

class RequestModified():
	def __init__(self, hash):
		self.hash = hash
		self.time_str = None
		self.time_int = None
