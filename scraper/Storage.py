# import redis
import threading

from .Thread import *

class Storage():
	def __init__(self, board):
		self.board = board
		
		self.lock = threading.Lock()
		
		self.conn = None
	
	def connect(self):
		pass
