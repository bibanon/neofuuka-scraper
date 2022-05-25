import redis
import threading

from .Thread import *

class Storage():
	def __init__(self, board):
		self.board = board
		
		self.lock = threading.Lock()
		
		self.conn = None
		
		if (
			self.board.conf.get("redisHost") and
			self.board.conf.get("redisPort")
		):
			try:
				self.conn = \
					redis.Redis(
						host=self.board.conf.get("redisHost"),
						port=self.board.conf.get("redisPort"),
						socket_timeout=3,
						socket_connect_timeout=3,
						health_check_interval=20,
					)
			except:
				pass
	
	def key(self, key):
		prefix = self.board.conf.get("redisPrefix")
		
		if prefix == None:
			prefix = "neofuuka_scraper"
		
		key = ([prefix] + key)
		key = (str(x) for x in key)
		key = ".".join(key)
		
		return key
