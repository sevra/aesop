# stdlib imports
from collections import namedtuple

# local imports
from util.keymap import Keymap, Bind

YX = namedtuple('YX', 'y x')


class Window(object):
   def __init__(self, parent, name, y, x, lines, cols):
      self.name = name
      self.parent = parent
      self.win = parent.derwin(lines, cols, y, x) if parent else None
      self.max = YX(*self.win.getmaxyx()) if parent else None
      self.beg = YX(*self.win.getbegyx()) if parent else None
      self.keymap = Keymap()

   def __getattr__(self, attr):
      return getattr(self.win, attr)


class WindowController(dict):
   @property
   def max(self):
      return self.root.max

   def __init__(self, rootwin):
      self['root'] = Window(None, 'root', *([None]*4))
      self['root'].win = rootwin
      self['root'].max = YX(*rootwin.getmaxyx())
      self['root'].beg = YX(*rootwin.getbegyx())
      self.active = None

   def __getattr__(self, name):
      return self[name]

   def __delattr__(self, name):
      del self[name]

   def add(self, name, y=0, x=0, lines=0, cols=0, parent=None):
      self[name] = Window(parent or self.root, name, y, x, lines, cols)

   def key_lookup(self, key, window=None):
      if not window: window = self.active
      
      if key in window.keymap:
         return window.keymap[key]
      elif window.parent:
         return self.key_lookup(key, window.parent)
      else:
         raise Exception('key %s not implemented' % key)

   def refresh(self):
      self.root.refresh()

   def apply(self, attr, *args, **kargs):
      for win in self:
         getattr(win, attr)(*args, **kargs)

   def __iter__(self):
      for key in sorted(self.keys()):
         yield self[key]
