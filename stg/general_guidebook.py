#!/usr/bin/env python
# encoding: utf-8
"""
Provide information about products the system expects, how they're stored
in the files, and how to manage them during the process of regridding.

:author:       Eva Schiffer (evas)
:contact:      evas@ssec.wisc.edu
:organization: Space Science and Engineering Center (SSEC)
:copyright:    Copyright (c) 2014 University of Wisconsin SSEC. All rights reserved.
:date:         Jan 2014
:license:      GNU GPLv3
:revision:     $Id$
"""
__docformat__ = "restructuredtext en"

from constants import *

import sys
import logging

from stg.dry import dry

LOG = logging.getLogger(__name__)

def parse_datetime_from_filename (file_path) :
    """parse the given file_name_string and create an appropriate datetime object
    that represents the datetime indicated by the file name; if the file name does
    not represent a pattern that is understood, None will be returned
    """
    
    datetime_to_return = None
    
    guidebook = dry('guidebooks', 'is_my_file', file_path)
    datetime_to_return = guidebook.parse_datetime_from_filename(file_path)

    return datetime_to_return

def get_satellite_from_filename (file_path) :
    """given a file name, figure out which satellite it's from
    if the file does not represent a known satellite name
    configuration None will be returned
    """
    
    satellite_to_return = None
    instrument_to_return = None
    
    guidebook = dry('guidebooks', 'is_my_file', file_path)
    satellite_to_return, instrument_to_return = guidebook.get_satellite_from_filename(file_path)

    return satellite_to_return, instrument_to_return

def get_variable_names (file_path, user_requested_names=[ ]) :
    """get a list of variable names we expect to process from the file
    """
    
    var_names = set ( )
    
    guidebook = dry('guidebooks', 'is_my_file', file_path)
    var_names.update(guidebook.get_variable_names(user_requested_names))

    return var_names

def main():
    import optparse
    from pprint import pprint
    usage = """
%prog [options] filename1.hdf

"""
    parser = optparse.OptionParser(usage)
    parser.add_option('-v', '--verbose', dest='verbosity', action="count", default=0,
            help='each occurrence increases verbosity 1 level through ERROR-WARNING-INFO-DEBUG')
    parser.add_option('-r', '--no-read', dest='read_hdf', action='store_false', default=True,
            help="don't read or look for the hdf file, only analyze the filename")
    (options, args) = parser.parse_args()
    
    levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    logging.basicConfig(level = levels[min(3, options.verbosity)])
    
    LOG.info("Currently no command line tests are set up for this module.")

if __name__ == '__main__':
    sys.exit(main())
