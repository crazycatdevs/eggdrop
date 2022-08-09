from dataclasses import dataclass
from typing import Callable
import re
import uuid
import sys
from pprint import pprint, pformat
import eggdrop
from eggdroppy.flags import FlagRecord, FlagMatcher
from eggdroppy.cmds import putmsg, putnotc
from dataclasses import dataclass
from datetime import datetime

bindtypes = {
  "pub": {"args": ("nick", "host", "handle", "channel", "text"), "reply": "chanmsg"},
  "pubm": {"args": ("nick", "host", "handle", "channel", "text"), "reply": "chanmsg"},
  "msg": {"args": ("nick", "host", "handle", "text"), "reply": "privmsg"},
  "msgm": {"args": ("nick", "host", "handle", "text"), "reply": "privmsg"},
  "dcc": {"args": ("handle", "idx", "text"), "reply": "dcc"},
  "join": {"args": ("nick", "host", "handle", "channel"), "reply": "privnotc"}
"""
  "fil": {"args": ("handle", "idx", "text"), "reply": "xxx"},
  "notc": {"args": ("nick", "host", "handle", "text", "dest"), "reply": "xxx"},
  "part": {"args": ("nick", "host", "handle", "channel", "msg"), "reply": "xxx"},
  "sign": {"args": ("nick", "host", "handle", "channel", "reason"), "reply": "xxx"},
  "kick": {"args": ("nick", "host", "handle", "channel", "topic"), "reply": "xxx"},
  "nick": {"args": ("nick", "host", "handle", "channel", "newnick"), "reply": "xxx"},
  "mode": {"args": ("nick", "host", "handle", "channel", "mode", "target"), "reply": "xxx"},
  "ctcp": {"args": ("nick", "host", "handle", "dest", "key", "text"), "reply": "xxx"},
  "ctcr": {"args": ("nick", "host", "handle", "dest", "key", "text"), "reply": "xxx"},
  "raw": {"args": ("from", "key", "text"), "reply": "xxx"},
  "bot": {"args": ("bot", "cmd", "text"), "reply": "xxx"},
  "chon": {"args": ("handle", "idx"), "reply": "xxx"},
  "chof": {"args": ("handle", "idx"), "reply": "xxx"},
  "sent": {"args": ("nick", "handle", "file"), "reply": "xxx"},
  "rcvd": {"args": ("nick", "handle", "file"), "reply": "xxx"},
  "chat": {"args": ("handle", "channel", "text"), "reply": "xxx"},
  "link": {"args": ("bot", "via"), "reply": "xxx"},
  "disc": {"args": ("bot"), "reply": "xxx"},
  "splt": {"args": ("nick", "host", "handle", "channel"), "reply": "xxx"},
  "rejn": {"args": ("nick", "host", "handle", "channel"), "reply": "xxx"},
  "filt": {"args": ("idx", "text"), "reply": "xxx"},
  "need": {"args": ("channel", "type"), "reply": "xxx"},
  "flud": {"args": ("nick", "host", "handle", "channel", "type"), "reply": "xxx"},
  "note": {"args": ("from", "to", "text"), "reply": "xxx"},
  "act": {"args": ("handle", "channel", "action"), "reply": "xxx"},
  "wall": {"args": ("from", "msg"), "reply": "xxx"},
  "bcst": {"args": ("bot", "channel", "text"), "reply": "xxx"},
  "chjn": {"args": ("bot", "host", "handle", "channel", "flag", "idx"), "reply": "xxx"},
  "chpt": {"args": ("bot", "handle", "channel", "idx"), "reply": "xxx"},
  "time": {"args": ("min", "hour", "day", "month", "year"), "reply": "xxx"},
  "away": {"args": ("bot", "idx", "text"), "reply": "xxx"},
  "load": {"args": ("module"), "reply": "xxx"},
  "unld": {"args": ("module"), "reply": "xxx"},
  "nkch": {"args": ("old", "new"), "reply": "xxx"},
  "evnt": {"args": ("type"), "reply": "xxx"},
  "lost": {"args": ("nick", "handle", "path", "bytes", "length"), "reply": "xxx"},
  "tout": {"args": ("nick", "handle", "path", "bytes", "length"), "reply": "xxx"},
  "out": {"args": ("queue", "text", "sent"), "reply": "xxx"},
  "cron": {"args": ("min", "hour", "day", "month", "weekday"), "reply": "xxx"},
  "log": {"args": ("channel", "text", "level"), "reply": "xxx"},
  "tls": {"args": ("idx"), "reply": "xxx"},
  "die": {"args": ("reason"), "reply": "xxx"},
  "ircaway": {"args": ("nick", "host", "handle", "channel", "msg"), "reply": "xxx"},
  "invt": {"args": ("nick", "host", "handle", "channel", "invitee"), "reply": "xxx"},
  "rawt": {"args": ("from", "key", "text", "tag"), "reply": "xxx"},
  "account": {"args": ("nick", "host", "handle", "channel", "account"), "reply": "xxx"},
  "isupport": {"args": ("key", "isset", "value"), "reply": "xxx"},
  "monitor": {"args": ("nick", "online"), "reply": "xxx"}
"""
}

@dataclass
class IRCUser:
  nick: str
  host: str
  account: str
  lastseen: datetime = None
  joined: datetime = None

@dataclass
class Bind:
  bindtype: str
  flags: str
  mask: str
  callback: Callable
  hits: int = 0

  @property
  def id(self):
    return f'{self.bindtype}{hex(id(self))[2:]}'

class BindCallback:

  @staticmethod
  def make_replyfunc(replytype, argdict):
    replyfunc = None
    if replytype == "chanmsg":
      def replyfunc(response):
        putmsg(argdict["channel"], response)
    elif replytype == "privmsg":
      def replyfunc(response):
        putmsg(argdict["nick"], response)
    elif replytype == "privnotc":
      def replyfunc(response):
        putnotc(argdict["nick"], response)
    elif replytype == "dcc":
      def replyfunc(response):
        # TODO: putdcc
        print(f"Python DCC response: {response}")
    return replyfunc

  def __init__(self, bindtype, mask, callback : Callable):
    self.__callback = callback
    self.__bindtype = bindtype
    self.__mask = mask

  def __call__(self, *args):
    pprint(args)
    bindinfo = bindtypes[self.__bindtype]

    kwargs = {"bindtype": self.__bindtype, "mask": self.__mask}
    kwargs.update(zip(bindinfo["args"], args))
    if "nick" in kwargs:
      ircuser_dict = eggdrop.findircuser(kwargs["nick"], kwargs["channel"]) if "channel" in kwargs else eggdrop.findircuser(kwargs["nick"])
      kwargs["ircuser"] = IRCUser(**ircuser_dict)
    if "reply" in bindinfo:
      kwargs["reply"] = self.make_replyfunc(bindinfo["reply"], argdict=kwargs)

    pprint(kwargs)
    self.__callback(**kwargs)

  def __str__(self):
    return self.__callback.__name__

class BindType:
  """ A BindType is an event that can trigger an Eggdrop response

  Each event that Eggdrop refers to, called a bind, requires a :class:`BindType` to be loaded by the
  :class:`Binds` class.

  Args:
    bindtype (string): A string representing one of the core Eggdrop bind types
    managed (bool): True if bindtype is managed by Eggdrop
  """
  def __init__(self, bindtype, managed):
    self.__bindtype = bindtype
    self.__managed = managed
    self.__binds = {}

  @staticmethod
  def make_callback_func(bindtype, mask, callback):
    return BindCallback(bindtype, mask, callback)

  def add(self, mask : str, callback : Callable, flags : str = "-"):
    """ Register a new bind event

    Adds a new :class:`BindType` attribute to a :class:`Bind` object.

    Args:
      flags (object): a flag object, we'll figure this out soon
      mask (str): mask or command or something, maybe find a better word here
      callback (method): The name of the function you wish to call when the event is triggered
    """
    cb = self.make_callback_func(bindtype=self.__bindtype, mask=mask, callback=callback)
    bind = Bind(flags=flags, mask=mask, callback=cb, bindtype=self.__bindtype)
    self.__binds[bind.id] = bind
    if self.__managed:
      eggdrop.bind(self.__bindtype, flags, mask, cb)

  def delete(self, bindid):
    bind = self.__binds[bindid]
    if self.__managed:
      eggdrop.unbind(self.__bindtype, bind.flags, bind.mask, bind.callback)
    if bindid in self.__binds:
      del self.__binds[bindid]

  def list(self):
    """ List all binds of the ``bindtype``

    Returns:
      list: A list of binds, in the format {A B C D}
    """
    return self.__binds

  def all(self):
    return self.list()

  def __str__(self):
    return f"{self.__bindtype}-binds: {str(self.__binds)}"

class Binds:
  """ A :class:`Binds` object holds a collection of :class:`BindTypes` objects

    All binds that are added to Eggdrop are collected and accessed through a :class:`Binds` object. Each
    event type that Eggdrop reacts to is added to the :class:`Binds` object as a bind via a
    :class:`BindTypes` object.

    Args: None
  """
  def __init__(self):
    self.__binds = {x: BindType(x, True) for x in bindtypes.keys()}

  def __getattr__(self, name):
    return self.__binds[name]

  def all(self):
    """ Lists all binds registered with the object

    Returns:
      list: A list, or maybe a dict? of all binds
    """
    return self.__binds

  def types(self):
    """ Lists all :class:`BindType` attributes added to the :class:`Binds` object

    Returns:
      list: maybe a list? of attributes
    """
    return self.__binds.keys()

  def __str__(self):
    return [{x: [str(b) for b in y]} for x, y in self.__binds.items()]


__allbinds = Binds()

for bindtype in __allbinds.types():
  setattr(sys.modules[__name__], bindtype, getattr(__allbinds, bindtype))

def all():
  return __allbinds.all()

def types():
  return __allbinds.types()

def print_all(reply, **kwargs):
  reply("{0: <8} | {1: <18} | {2: <12} | {3: <24} | {4}".format('ID', 'function', 'flags', 'mask', 'hits'))
  for i in types():
    if __allbinds.all()[i].all():
      reply("-"*78)
      reply(f'{i:<8}')
      reply("-"*78)
      for j in __allbinds.all()[i].all().keys():
        reply(f'{j} | {str(__allbinds.all()[i].all()[j].callback):<18} | {str(__allbinds.all()[i].all()[j].flags):<12} | {__allbinds.all()[i].all()[j].mask:<24} | {__allbinds.all()[i].all()[j].hits:<4}')
  reply("-"*78)

__allbinds.dcc.add(mask='pybinds', callback=print_all)
