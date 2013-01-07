#!/usr/bin/env python

# stdlib imports
import os, sys, signal, curses, datetime
from select import select, error
from mplayer import MPlayer, PLAYING, PAUSED, STOPPED, SelectQueue
from itertools import cycle

# local imports
from util.window import WindowController
from util.keymap import Bind
from util.playlist import Playlist
from util.browser import Browser
from util.misc import stom, NamedDict, Signaler, PlayerState, Handler

if True:
   import logging

   logging.basicConfig(
      filename = '/home/psev/code/python/aesop/log', 
      filemode = 'w',
      format = '%(levelname)s: %(name)s: %(processName)s: %(asctime)s: %(message)s',
      datefmt = '%H:%M:%S',
   )
   log = logging.getLogger('Aesop')
   log.setLevel(logging.INFO)


class StateHandler(Handler):
   def on_init(self):
      self.win.hline(2, 0, curses.ACS_HLINE, self.win.parent.max.x)
      self.file = None
      self.path = None
      self.display()
      self.attach('chdir', self.set_path)

   def on_change(self):
      self.display()

   def on_play(self):
      self.file = self.player.get_file_name()
      self.display()

   def on_stop(self):
      self.file = None
      self.display()

   def display(self):
      win = self.win
      state = None
      if self.playing:
         state = 'Playing'
      elif self.paused:
         state = 'Paused'
      elif self.stopped:
         state = 'Stopped'

      win.move(0, 0)
      win.clrtoeol()
      win.insstr('File:%s State:%s' % (self.file, state))
      win.move(1, 0)
      win.clrtoeol()
      win.insstr('Path:%s' % self.path, curses.A_BOLD)
      win.refresh()

   def set_path(self, path):
      self.path = path
      self.display()


class HelpHandler(Handler):
   def __init__(self, win, player, wins):
      self.wins = wins
      super(HelpHandler, self).__init__(win, player)

   def on_init(self):
      self.win.keymap.add(
         Bind('Refresh help page.', ['r'], self.display),
      )
      self.display()

   def display(self):
      self.win.clear()
      i = 0
      for win in self.wins:
         if not win.keymap: continue
         self.win.insstr(i, 0, win.name.title())
         i += 1
         for info, keys in win.keymap.help:
            self.win.insstr(i, 1, '%s - %s' % (', '.join(keys), info))
            i += 1
         i += 1
      self.win.refresh()


class ProgressHandler(Handler):
   def on_init(self):
      self.win.hline(0, 0, curses.ACS_HLINE, self.win.parent.max.x)
      self.tpos = 0
      self.tlen = 0
      self.display()

   def on_play(self):
      self.tpos = 0
      self.tlen = self.player.get_time_length()
   
   def on_stop(self):
      self.tlen = 0
      self.display()

   def while_playing(self):
      self.display()

   def display(self, inc=None):
      win = self.win
      win.move(1, 0)
      win.clrtoeol()
      if not inc:
         tpos = self.tpos = self.player.get_time_pos()
      else:
         self.tpos += inc
         if self.tpos > self.tlen:
            self.tpos = self.tlen
         elif self.tpos < 0:
            self.tpos = 0
         tpos = self.tpos
      tlen = self.tlen
      ppos = (tpos / tlen) * 100 if tlen else 0
      win.insstr('Time: %d:%02d/%d:%02d' % tuple(stom(tpos) + stom(tlen)))
      win.insstr('Percent: %d | ' % ppos)
      pct = round(self.win.parent.max.x * ppos / 100)
      win.move(2, 0)
      win.insstr('%s%s%s' % ('='*(pct-1), '>', '-'*(self.win.parent.max.x-pct)))
      win.refresh()

   def seek(self, i=10):
      if self.playing:
         self.player.seek(i)
      else:
         self.player.seek(self.tpos + i, 2)
         self.display(i)


class BrowserHandler(Handler):
   def __init__(self, win, player, exts, browser=None):
      self.browser = browser or Browser(exts)
      self.exts = exts
      self.last_mouse_event = None
      super(BrowserHandler, self).__init__(win, player)

   def on_init(self):
      self.win.keymap.add(
         Bind('Play highlighted item.', ['\n'], self.enter),
         Bind('Move cursor up.', ['KEY_UP', 'k'], self.goto, -1),
         Bind('Move cursor down.', ['KEY_DOWN', 'j'], self.goto, 1),
         Bind('Move cursor to start of page.', ['KEY_PPAGE', 'K'], self.goto, 0, False),
         Bind('Move cursor to end of page.', ['KEY_NPAGE', 'J'], self.goto, lambda : self.browser.len - 1, False),
      )
      self.display()
      self.emit('chdir', self.browser.path)

   def on_mouse(self, event):
      id, x, y, z, state = event
      log.info('MOUSE EVENT: (%s, %s) :: %s' % (x, y, state))
      beg = self.win.beg
      if not y - beg.y < self.browser.len: return
      if state & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED):
         self.goto(y - beg.y, False)
      elif state & (curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED):
         self.goto(y - beg.y, False)
         self.enter()
         
      if state & 16777218: #| 17039360 | 17301504:
         self.goto(y - beg.y, False)

      self.last_mouse_event = event
   
   def display(self):
      self.win.clear()
      i = 0
      for file in self.browser[:self.win.max.y]:
         color = curses.color_pair(1 if os.path.isdir(file) else 2)
         self.win.insstr(i, 1, file, color | curses.A_BOLD)
         if i == self.browser.idx:
            self.win.chgat(curses.color_pair(3) | curses.A_BOLD)
         i += 1
      self.win.refresh()

   def goto(self, i, rel=True):
      if callable(i): i = i()
      self.browser.idx = self.browser.idx + i if rel else i
      self.display()

   def enter(self):
      if os.path.isdir(self.browser.current):
         self.browser.chdir(self.browser.current)
         self.emit('chdir', self.browser.path)
      else:
         self.player.loadfile(os.path.abspath(self.browser.current))
      self.display()


class Aesop(Signaler, PlayerState):
   @property
   def active(self):
      return self._active

   @active.setter
   def active(self, handler):
      self._active = handler
      self.windows.active = handler.win

   def __init__(self, rootwin):
      log.info('Initialized')
      self.windows = WindowController(rootwin)
      self.handlers = NamedDict()
      self.player = MPlayer(['-vo', 'vdpau', '-ao', 'pulse'])
      self.setup()
      self.run()

   def setup(self):
      self.timeout = None
      self.player.defaults['default'] = 0

      curses.curs_set(False)
      curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
      curses.mouseinterval(0)

      curses.use_default_colors()
      curses.init_pair(1, curses.COLOR_BLUE, 0)
      curses.init_pair(2, curses.COLOR_CYAN, 0)
      curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
      curses.init_pair(4, curses.COLOR_YELLOW, 0)

      self.windows.add('help', 3, 0, self.windows.max.y-6, self.windows.max.x-1)
      self.handlers.help = HelpHandler(self.windows.help, self.player, self.windows)

      self.windows.add('state', 0, 0, 3, self.windows.max.x)
      self.handlers.state = StateHandler(self.windows.state, self.player)

      self.windows.add('progress', self.windows.max.y-3, 0)
      self.handlers.progress = ProgressHandler(self.windows.progress, self.player)

      exts = [ 'avi', 'wmv', 'mkv', 'mpg', ]
      self.windows.add('browser', 3, 0, self.windows.max.y-6, self.windows.max.x-1)
      self.handlers.browser = BrowserHandler(self.windows.browser, self.player, exts)

      self.windows.apply('keypad', 1) # turn keypad on for all windows

      self.active = self.handlers.browser
      active = cycle([self.handlers.help, self.handlers.browser])

      signal.signal(signal.SIGWINCH, lambda *args : self.handle('resize'))
      self.windows.root.keymap.add(
         Bind(None, ['KEY_RESIZE'], lambda : self.handle('resize')),
         Bind(None, ['KEY_MOUSE'], self.mouse),
         Bind('Close Aesop.', ['q'], self.quit),
         Bind('Toggle pause.', ['p'], self.player.pause),
         Bind('Stop play.', ['x'], self.player.stop),
         Bind('Seek forward 10 seconds', ['KEY_RIGHT', 's'], self.handlers.progress.seek, 10),
         Bind('Seek backward 10 seconds', ['KEY_LEFT', 'h'], self.handlers.progress.seek, -10),
         Bind('Cycle between help, browser and playlist windows.', ['\t'],  self.set_active, lambda : next(active)),
      )

   def run(self):
      rfds = [
         sys.stdin,
         self.player.notifier,
      ]

      while True:
         try: rl, wl, el = select(rfds, [], [], self.timeout)
         except error: continue

         if sys.stdin in rl:
            try:
               bind = self.windows.key_lookup(self.windows.active.getkey())
               bind.func(*bind.args, **bind.kargs)
            except Exception as err:
               log.warning(err)
            curses.flushinp()

         if self.player.notifier in rl:
            self.apply_state(self.player.notifier.get())

         if self.playing:
            self.handle('playing')

   def apply_state(self, state):
      self.handle('change')
      if self.playing:
         self.player.defaults['prefix'] = ''
         self.handle('play')
         self.timeout = 1
      elif self.paused:
         self.player.defaults['prefix'] = 'pausing_keep'
         self.handle('pause')
         self.timeout = None
      elif self.stopped:
         self.player.defaults['prefix'] = ''
         self.handle('stop')
         self.timeout = None
      self.windows.refresh()

   def handle(self, action, *args, **kargs):
      for handler in self.handlers:
         if action == 'playing':
            prefix = 'while_'
         else:
            prefix = 'on_'
         getattr(self.handlers[handler], prefix + action)(*args, **kargs)

   def set_active(self, handler):
      if callable(handler): handler = handler()
      self.active = handler
      handler.display()
         
   def mouse(self):
      id, x, y, z, state = event = curses.getmouse()
      if self.active.win.enclose(y, x):
         self.active.on_mouse(event)

   def quit(self):
      self.player.kill()
      raise SystemExit()


curses.wrapper(Aesop)
