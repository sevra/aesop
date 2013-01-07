from collections import namedtuple


class Bind(namedtuple('Bind', ['help', 'keys', 'func', 'args', 'kargs'])):
   def __new__(cls, help, keys, func, *args, **kargs):
      return super(Bind, cls).__new__(cls, help, keys, func, args, kargs)


class Keymap(dict):
   def __init__(self, *binds):
      self.help = []
      self.add(*binds)

   def add(self, *binds):
      for bind in binds:
         self.help.append([bind.help, bind.keys])
         if isinstance(bind, Bind):
            for key in bind.keys:
               if not self.get(key):
                  self[key] = bind
               else:
                  raise Exception('Key aleady bound in this keymap')
         else:
            raise ValueError('Item is not of Bind class')
