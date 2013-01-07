class Playlist(list):
	def __init__(self, *args):
		self.cont = True
		self.consume = False
		self.idx = 0
		super(Playlist, self).__init__(*args)

	def next(self):
		return self.goto(1)

	def prev(self):
		return self.goto(-1)

	def current(self):
		return self.pop(self.idx) if self.consume else self[self.idx]

	def goto(self, i):
		self.idx += i
		return self.current()
