import threading

class Thread(threading.Thread):
	def __init__(self, board, **args):
		super().__init__()
		
		self.daemon = True
		
		self.board = board
		self.index = args.get("index", 0)
		self.type = args.get("type", None)
		
		self.name = f"/{board.name}/ {self.__class__.__name__}"
		
		if self.type != None:
			self.name = f"{self.name} {self.type.name}"
		
		if self.index > 0:
			self.name = f"{self.name} #{self.index}"
	
	def run(self):
		# self.board.log(self, "Thread start")
		self.board.sleep(0.01)
		pass
