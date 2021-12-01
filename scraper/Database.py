import sys
import enum
import pymysql
import threading

try:
	import MySQLdb
	import MySQLdb.cursors
except:
	pass

class Database():
	def __init__(self, board):
		self.board = board
		
		self.lock = threading.Lock()
		
		self.lock.acquire()
		
		self.conn = None
		
		self.module = DatabaseModule.PYMYSQL
		
		if "MySQLdb" in sys.modules:
			self.module = DatabaseModule.MYSQLDB
	
	def connect(self):
		if self.conn == None:
			self.lock.acquire(False)
			
			self.board.log(self, "Connecting to database...")
			
			try:
				args = {
					"host": self.board.conf.get("dbSrvHost", "localhost"),
					"port": self.board.conf.get("dbSrvPort", 3306),
					"user": self.board.conf.get("dbUserName", "neofuuka"),
					"password": self.board.conf.get("dbUserPass", "neofuuka"),
					"db": self.board.conf.get("dbDatabase", "neofuuka"),
					"charset": self.board.conf.get("dbCharset", "utf8mb4"),
				}
				
				if self.module == DatabaseModule.PYMYSQL:
					self.conn = \
						pymysql.connect(
							**args,
							cursorclass = pymysql.cursors.DictCursor
						)
				
				if self.module == DatabaseModule.MYSQLDB:
					self.conn = \
						MySQLdb.connect(
							**args,
							cursorclass = MySQLdb.cursors.DictCursor
						)
				
				if self.conn == None:
					raise Exception("Invalid database module")
				
				self.board.log(self, "Database connection successful")
				
				self.lock.release()
			except Exception as err:
				self.board.log(self, f"Database connection failed: {repr(err)}")
				self.conn = None
	
	def disconnect(self):
		self.lock.acquire(False)
		
		if self.conn != None:
			self.conn.close()
			self.conn = None
	
	def error(self, err = None):
		self.lock.acquire(False)
		
		self.board.log(self, "An error occurred: {}".format(repr(err) if err else "(unknown)"))
		
		try:
			self.conn.rollback()
		except:
			pass
		
		try:
			self.conn.ping(True)
			self.lock.release()
		except:
			self.disconnect()
			pass
	
	def cursor(self, cur = None):
		return self.conn.cursor(cur)
	
	def commit(self):
		return self.conn.commit()
	
	def act_start(self, block=True, timeout=-1):
		return self.lock.acquire(block, timeout)
	
	def act_finish(self):
		return self.lock.release()

class DatabaseModule(enum.Enum):
	PYMYSQL = enum.auto()
	MYSQLDB = enum.auto()
