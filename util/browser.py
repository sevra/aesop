import os

class Browser(list):
   @property
   def idx(self):
      return self._idx

   @idx.setter
   def idx(self, val):
      val = val % self.len
      if val < 0:
         self._idx = self.len - 1
      elif val > self.len - 1:
         self._idx = 0
      else:
         self._idx = val

   @property
   def current(self):
      return self[self.idx]

   def __init__(self, exts, path=None):
      self.trail = []
      self.exts = exts
      self._idx = 0
      self.chdir(path or os.getcwd())

   def chdir(self, path=None):
      self.clear()
      self.path = os.path.abspath(path or self.current)
      self.dirs, self.files = map(sorted, next(os.walk(self.path))[1:])
      self.insert(0, '..')
      self.extend(self.dirs)
      self.extend(filter(lambda file: file.split(os.extsep)[-1:][0] in self.exts, self.files))
      self.len = len(self)
      if path == '..':
         try:
            self.idx = self.trail.pop()
         except IndexError:
            self.idx = 0
      else:
         self.trail.append(self.idx)
         self.idx = 0
      os.chdir(path)
