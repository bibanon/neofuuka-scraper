import os
import time
import hashlib

from .Thread import *
from .ItemFile import *
from .Requests import *

class FetcherFiles(Thread):
	def run(self):
		super().run()
		
		while True:
			if self.board.stop(): break
			
			file = None
			
			with self.board.lock:
				for file1 in self.board.save_files:
					if file1.type1 != self.type:
						continue
					
					if file1.error_count > 0:
						if (time.time() - file1.error_last_time) < file1.get_retry_timer():
							continue
					
					file = file1
					self.board.save_files.remove(file)
					break
			
			if not file:
				self.board.sleep(0.3)
				continue
			
			file_path = file.get_path()
			file_path_t = (file_path + ".tmp")
			
			try:
				if os.path.isfile(file_path):
					if (
						file.type1 == FileType1.SRC and
						self.board.conf.get("fileMismatchRedo", False) and
						os.path.getsize(file_path) != file.size
					):
						# delete the file and redownload
						os.path.remove(file_path)
					else:
						if (
							file.type1 == FileType1.SRC and
							self.board.conf.get("fileTouchOnDupe", False)
						):
							# update last mod time
							os.utime(file_path)
						
						self.board.sleep(0.003)
						continue
				
				# self.board.log(self, f"Downloading {file.time}")
				
				attempt = 0
				
				while True:
					res = \
						self.board.requests.make(
							url = file.get_link(),
							type = RequestType.FILE
						)
					
					try:
						if res.code != 200:
							raise Exception(f"code {res.code}")
						
						if file.type1 == FileType1.SRC:
							if len(res.data) != file.size:
								raise Exception("bad size")
							
							hash = hashlib.md5()
							hash.update(res.data)
							hash = hash.digest()
							
							if hash != file.hash:
								raise Exception("bad hash")
						
						os.makedirs(
							name = os.path.dirname(file_path),
							exist_ok = True
						)
						
						tmp = open(file_path_t, "wb")
						tmp.write(res.data)
						tmp.close()
						
						os.rename(file_path_t, file_path)
						
						break
					except Exception as err:
						try:
							if os.path.isfile(file_path): os.remove(file_path)
							if os.path.isfile(file_path_t): os.remove(file_path_t)
						except:
							pass
						
						attempt += 1
						
						if (
							attempt >= 3 or
							res.code == 404
						):
							self.board.log(self.board, f"Download fail {file.time} ({str(err)})")
							
							file.error_count += 1
							file.error_last_time = time.time()
							file.error_last_type = FileFetchErr.UNKNOWN
							
							if res.code == 404:
								file.error_last_type = FileFetchErr.NOTFOUND
							
							if file.error_count <= file.get_retry_count():
								with self.board.lock:
									self.board.save_files.append(file)
							
							break
						
						self.board.sleep(1.0)
						continue
				
				self.board.sleep(0.003)
				continue
			except:
				pass
			
			self.board.sleep(1.0)
			continue
