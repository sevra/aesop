from mplayer import PLAYING, PAUSED, STOPPED

stom = lambda secs : [secs / 60, secs % 60]


class NamedDict(dict):
   def __getattr__(self, name):
      return self[name]

   def __setattr__(self, name, val):
      self[name] = val

   def __delattr__(self, name):
      del self[name]


class Signaler(object):
   signals = {}

   def attach(self, sig, act):
      if not self.signals.get(sig):
         self.signals[sig] = []
      self.signals[sig].append(act)

   def detatch(self, sig, act):
      if self.signals[sig]:
         self.signals[sig].remove(act)
      else:
         raise ValueError() # TODO replace with better error message

   def emit(self, sig, *args, **kargs):
      for act in self.signals[sig]:
         act(*args, **kargs)


class PlayerState(object):
   @property
   def playing(self):
      return self.player.state == PLAYING

   @property
   def paused(self):
      return self.player.state == PAUSED

   @property
   def stopped(self):
      return self.player.state == STOPPED  


class Handler(Signaler, PlayerState):
   def __init__(self, win, player):
      self.win = win
      self.player = player
      self.on_init()

   def on_init(self):
      pass

   def on_change(self):
      pass

   def on_play(self):
      pass

   def on_pause(self):
      pass

   def on_stop(self):
      pass

   def while_playing(self):
      pass

   def on_resize(self):
      raise NotImplementedError('on_resize not implemented')

   def on_mouse(self, event):
      pass



