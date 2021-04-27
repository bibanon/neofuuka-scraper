import enum
import base64
import os

# from .Utils import *

class ItemFile():
	def __init__(self, post, type):
		self.board = None
		
		self.type1 = None # FileType1
		self.type2 = None # FileType2
		self.time = None
		self.hash = None
		self.type = None
		self.size = None
		
		self.time1 = None # asagi target name
		
		self.error_count = 0
		self.error_last_time = None
		self.error_last_type = None
		
		# init
		self.board = post.board
		self.type1 = type
		self.type2 = (FileType2.OP if post.is_opener() else FileType2.RP)
		self.time = post.file_time
		self.hash = post.file_hash
		self.type = post.file_type
		self.size = post.file_size
	
	def get_link(self):
		return (
			self.board.conf.get("sourceLinkFiles" + ("thb" if self.type1 == FileType1.THB else "src").capitalize()) +
			"/" + self.board.get_name_src() + "/" + str(self.time) + ("s.jpg" if self.type1 == FileType1.THB else ("." + self.type))
		)
	
	def get_path(self):
		path = self.board.conf.get("fileSavePath")
		path = path.format(board = self.board.get_name())
		
		path = \
			os.path.join(
				path,
				self.board.get_name(),
				("thumb" if self.type1 == FileType1.THB else "image"),
				str(self.time1)[0:4],
				str(self.time1)[4:6],
				(
					str(self.time1) +
					("s.jpg" if self.type1 == FileType1.THB else ("." + self.type))
				)
			)
		
		return path
		
		# TODO: for new stack
		
		path = \
			os.path.join(
				path,
				str(self.type1).lower(),
				self.hash.hex()[0:2],
				self.hash.hex()[2:4],
				(
					self.hash.hex() +
					(("." + str(self.type2).lower()) if self.type1 == FileType1.THB else "") +
					"." + self.type
				)
			)
		
		return path
	
	def get_retry_count(self):
		if self.error_last_type == FileFetchErr.NOTFOUND:
			if self.type1 == FileType1.THB:
				return 10
			else:
				return 5
		
		return 30
	
	def get_retry_timer(self):
		if self.error_last_type == FileFetchErr.NOTFOUND:
			return (60*15)
		
		return (60*5)

# created by FetcherFiles, for new schema
class ItemFileHash():
	def __init__(self, post, type, value):
		self.post = post
		self.type = type
		self.value = value

class FileType1(enum.Enum):
	THB = enum.auto() # thumbnail
	SRC = enum.auto() # original

class FileType2(enum.Enum):
	OP = enum.auto() # opening post
	RP = enum.auto() # reply post

class FileFetchErr(enum.Enum):
	UNKNOWN = enum.auto() # unknown error
	NOTFOUND = enum.auto() # 404 not found
