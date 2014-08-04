#!/usr/bin/env python
# encoding: utf-8
"""
dry.py is a basic module to keep us from repeating ourselves.

:author:       Nick Bearson (nickb)
:contact:      nickb@ssec.wisc.edu
:organization: Space Science and Engineering Center (SSEC)
:copyright:    Copyright (c) 2014 University of Wisconsin SSEC. All rights reserved.
:date:         Jul 2014
:license:      GNU GPLv3
:revision:     $Id$
"""
__docformat__ = "restructuredtext en"

import importlib
import os, sys
import logging

LOG = logging.getLogger(__name__)

def dry(path, test_function, test_data):
  """
  Given a directory full of similar modules, find the one that matches
  our test case and return it.

  FIXME: is there really not a better way to do test-and-load?
  """
  relpath = os.path.dirname(__file__) + "/" + path
  sys.path.insert(0, relpath)
  for module in os.listdir(relpath):
    if module == '__init__.py' or module[-3:] != '.py':
      continue
    mod = importlib.import_module(module[:-3])
    f = getattr(mod, test_function)
    if f(test_data):
      print "Returning ", mod
      return mod
  LOG.error("No modules match: ", path, test_function, test_data)
  raise RuntimeError