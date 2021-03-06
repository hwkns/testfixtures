# Copyright (c) 2008-2011 Simplistix Ltd
# See license.txt for license details.

import atexit
import logging
import warnings

from testfixtures.comparison import compare
from testfixtures.utils import wrap

class LogCapture(logging.Handler):
    """
    These are used to capture entries logged to the Python logging
    framework and make assertions about what was logged.

    :param names: A sequence of strings containing the dotted names of
                  loggers to capture. By default, the root logger is
                  captured.
                  
    :param install: If `True`, the :class:`LogCapture` will be
                    installed as part of its instantiation.
    """
    
    instances = set()
    atexit_setup = False
    installed = False
    
    def __init__(self, names=None, install=True, level=1):
        logging.Handler.__init__(self)
        if not isinstance(names,tuple):
            names = (names,)
        self.names = names
        self.level = level
        self.oldlevels = {}
        self.oldhandlers = {}
        self.clear()
        if install:
            self.install()

    @classmethod
    def atexit(cls):
        if cls.instances:
            warnings.warn(
                'LogCapture instances not uninstalled by shutdown, '
                'loggers captured:\n'
                '%s' % ('\n'.join((str(i.names) for i in cls.instances)))
                )
        
    def clear(self):
        "Clear any entries that have been captured."
        self.records = []
        
    def emit(self, record):
        self.records.append(record)

    def install(self):
        """
        Install this :class:`LogHandler` into the Python logging
        framework for the named loggers.

        This will remove any existing handlers for those loggers and
        drop their level to 1 in order to capture all logging.
        """
        for name in self.names:
            logger = logging.getLogger(name)
            self.oldlevels[name] = logger.level
            self.oldhandlers[name] = logger.handlers
            logger.setLevel(self.level)
            logger.handlers = [self]
        self.instances.add(self)
        if not self.__class__.atexit_setup:
            atexit.register(self.atexit)
            self.__class__.atexit_setup = True

    def uninstall(self):
        """
        Un-install this :class:`LogHandler` from the Python logging
        framework for the named loggers.

        This will re-instate any existing handlers for those loggers
        that were removed during installation and retore their level
        that prior to installation.
        """
        if self in self.instances:
            for name in self.names:
                logger = logging.getLogger(name)
                logger.setLevel(self.oldlevels[name])
                logger.handlers = self.oldhandlers[name]
                if self in logging._handlers:
                    del logging._handlers[self]
                if self in logging._handlerList:
                    logging._handlerList.remove(self)
            self.instances.remove(self)

    @classmethod
    def uninstall_all(cls):
        "This will uninstall all existing :class:`LogHandler` objects."
        for i in tuple(cls.instances):
            i.uninstall()
        
    def actual(self):
        for r in self.records:
            yield (r.name,r.levelname,r.getMessage())
    
    def __str__(self):
        if not self.records:
            return 'No logging captured'
        return '\n'.join(["%s %s\n  %s" % r for r in self.actual()])

    def check(self,*expected):
        """
        This will compare the captured entries with the expected
        entries provided and raise an :class:`AssertionError` if they
        do not match.

        :param expected: A sequence of 3-tuples containing the
                         expected log entries. Each tuple should be of
                         the form (logger_name, string_level, message)
        """
        return compare(
            expected,
            tuple(self.actual()),
            recursive=False
            )

    def __enter__(self):
        return self
    
    def __exit__(self,type,value,traceback):
        self.uninstall()

class LogCaptureForDecorator(LogCapture):

    def install(self):
        LogCapture.install(self)
        return self
    
def log_capture(*names, **kw):
    """
    A decorator for making a :class:`LogCapture` installed an
    available for the duration of a test function.

    :param names: An optional sequence of names specifying the loggers
                  to be captured. If not specified, the root logger
                  will be captured.
    """
    level = kw.pop('level',1)
    l = LogCaptureForDecorator(names or None, install=False, level=level)
    return wrap(l.install,l.uninstall)

