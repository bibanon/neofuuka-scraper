import sys
import os
import time
import signal
import threading
import multiprocessing
import json

from .Board import *

FILE_SAVE = "./save.json"

class Scraper():
	def __init__(self, config, args):
		self.config = config
		self.args = args
		
		self.pid = None
		
		# stop signal
		self.stop1 = False
		
		# board list
		self.boards = None
		
		# shared stuff
		self.shared = None
	
	def run(self):
		# multiprocessing.set_start_method("spawn")
		
		self.boards = []
		self.shared = Shared()
		self.pid = os.getpid()
		
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
						board_conf,
						self.args
					)
				
				self.boards.append(board)
				
				time.sleep(0.1)
		except:
			print("Config parse error!")
			return 1
		
		timer = time.time()
		
		# start each board
		for board in self.boards:
			board.start()
		
		# handle signals
		signal.signal(signal.SIGINT, self.signal)
		signal.signal(signal.SIGTERM, self.signal)
		
		# wait for stop
		try:
			while True:
				time.sleep(0.1)
				
				# signal break
				if self.stop1: break
				
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
				if board.is_alive():
					wait = True
			
			if not wait: break
			
			time.sleep(0.1)
			
			continue
		
		return 0
	
	def signal(self, signum, frame):
		if self.stop1:
			sys.exit(1)
		
		self.set_stop()
	
	def set_stop(self):
		self.stop1 = True
		self.shared.stop.value = 1

class Shared():
	def __init__(self):
		self.stop = multiprocessing.Value("b", 0)
		self.lock = multiprocessing.Lock()
		self.print_lock = multiprocessing.RLock()
		self.request_lock = multiprocessing.Lock()
		self.request_time = multiprocessing.Value("d", 0.0)

class Schema(enum.Enum):
	NEO = enum.auto()
	ASAGI = enum.auto()
