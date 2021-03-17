import sys
import time
import signal
import threading
import json

from .Board import *

FILE_SAVE = "./save.json"

class Scraper():
	def __init__(self, config, args):
		self.config = config
		self.args = args
		
		# stop flag
		self.stop = False
		
		# board list
		self.boards = None
		
		# general scraper lock
		self.scraper_lock = threading.Lock()
		
		# global request throttling
		self.request_lock = threading.Lock()
		self.request_time = 0
		
		# TODO: use this to track global archived threads
		# periodically save it to a file and load on start
		self.archiveds = []
	
	def run(self):
		self.boards = []
		
		try:
			# load boards from config
			for board_name in self.config["boards"]:
				board_conf = {}
				board_conf.update(self.config["global"])
				board_conf.update(self.config["boards"][board_name])
				
				if board_conf.get("base"):
					board_conf.update(self.config["bases"][board_conf["base"]])
					board_conf.update(self.config["boards"][board_name])
				
				board = \
					Board(
						self,
						board_name,
						board_conf
					)
				
				self.boards.append(board)
				
				time.sleep(0.1)
		except:
			print("Config parse error!")
			return 1
		
		timer = time.time()
		
		# handle signals
		signal.signal(signal.SIGINT, self.signal)
		signal.signal(signal.SIGTERM, self.signal)
		
		# start each board
		for board in self.boards:
			board.start()
		
		# wait for stop
		try:
			while True:
				time.sleep(0.1)
				
				# signal break
				if self.stop: break
				
				# profiler break
				if (
					"prof" in self.args and
					(time.time() - timer) > 60
				):
					break
		except BaseException:
			pass
		
		self.set_stop()
		
		while True:
			wait = False
			
			for board in self.boards:
				if not board.stopped():
					wait = True
			
			if not wait: break
			
			time.sleep(0.1)
			
			continue
		
		return 0
	
	def signal(self, signum, frame):
		if self.stop:
			sys.exit(1)
		
		self.set_stop()
	
	def set_stop(self):
		self.stop = True
		
		if self.boards:
			for board in self.boards:
				board.set_stop()
	
	def save_read(self):
		pass
	
	def save_write(self):
		with self.scraper_lock:
			# FILE_SAVE
			pass

class Schema(enum.Enum):
	NEO = enum.auto()
	ASAGI = enum.auto()
