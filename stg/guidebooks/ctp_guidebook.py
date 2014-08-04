#!/usr/bin/env python
# encoding: utf-8
"""
Provide information about products the system expects in Rich Frey's per-orbit binary CTP files, how
they're stored in the files, and how to manage them during the process of regridding.

:author:       Nick Bearson (nickb)
:contact:      nickb@ssec.wisc.edu
:organization: Space Science and Engineering Center (SSEC)
:copyright:    Copyright (c) 2014 University of Wisconsin SSEC. All rights reserved.
:date:         Feb 2014
:license:      GNU GPLv3
:revision:     $Id$
"""
__docformat__ = "restructuredtext en"

from stg.constants import *

import sys
import os
import logging
import numpy
from datetime import datetime

LOG = logging.getLogger(__name__)

# variable names expected in the files

LATITUDE_NAME               = 'Latitude'
LONGITUDE_NAME              = 'Longitude'
CLOUD_TOP_PRESS_NAME        = 'Cloud_Top_Pressure'
CLOUD_TOP_HEIGHT_NAME       = 'Cloud_Top_Height'
CLOUD_TOP_TEMP_NAME         = 'Cloud_Top_Temperature'
EFFECTIVE_CLOUD_AMOUNT_NAME = 'Effective_Cloud_Amount'
METHOD_FLAG_NAME            = 'Retrieval_Method_Flag'
DAY_NIGHT_FLAG_NAME         = 'Day_Night_Flag'
DIRECTION_FLAG_NAME         = 'Direction_Flag'
VIEWING_ZENITH_NAME         = 'Viewing_Zenith'
SCAN_LINE_TIME_NAME         = 'Scan_Line_Time'
CLOUD_FRACTION_NAME         = 'Cloud_Fraction'
LAND_FRACTION_NAME          = 'Land_Fraction'
RESULTS_FLAG_NAME           = 'Results_Flag'
UTLS_FLAG_NAME              = 'UTLS_Flag'

# a map of what the caller calls variables to variable names in files
CALLER_VARIABLE_MAP     = {
                            'latitude':                     LATITUDE_NAME,
                            'lat':                          LATITUDE_NAME,

                            'longitude':                    LONGITUDE_NAME,
                            'lon':                          LONGITUDE_NAME,

                            'cloud top pressure':           CLOUD_TOP_PRESS_NAME,
                            'pressure':                     CLOUD_TOP_PRESS_NAME,

                            'cloud top height':             CLOUD_TOP_HEIGHT_NAME,
                            'height':                       CLOUD_TOP_HEIGHT_NAME,


                            'cloud top temperature':        CLOUD_TOP_TEMP_NAME,
                            'ctt5km':                       CLOUD_TOP_TEMP_NAME,
                            'cloud_top_temperature':        CLOUD_TOP_TEMP_NAME,

                            'amount':                       EFFECTIVE_CLOUD_AMOUNT_NAME,
                            'cloud amount':                 EFFECTIVE_CLOUD_AMOUNT_NAME,
                            'effective cloud amount':       EFFECTIVE_CLOUD_AMOUNT_NAME,

                          }


# just do everything by default 
EXPECTED_VARIABLES_IN_FILE = set([LATITUDE_NAME              ,
                                  LONGITUDE_NAME             ,
                                  CLOUD_TOP_PRESS_NAME       ,
                                  CLOUD_TOP_HEIGHT_NAME      ,
                                  CLOUD_TOP_TEMP_NAME        , 
                                  EFFECTIVE_CLOUD_AMOUNT_NAME, 
                                  METHOD_FLAG_NAME           , 
                                  DAY_NIGHT_FLAG_NAME        , 
                                  DIRECTION_FLAG_NAME        , 
                                  VIEWING_ZENITH_NAME        , 
                                  SCAN_LINE_TIME_NAME        , 
                                  CLOUD_FRACTION_NAME        , 
                                  LAND_FRACTION_NAME         , 
                                  RESULTS_FLAG_NAME          , 
                                  UTLS_FLAG_NAME             ,])

VALID_RANGES = {
                  LATITUDE_NAME               :[-90.0, 90.0],
                  LONGITUDE_NAME              :[-180.0, 180.0],
                  DAY_NIGHT_FLAG_NAME         :[1, 2],
                  DIRECTION_FLAG_NAME         :[1, 2],
                  VIEWING_ZENITH_NAME         :[0, 90],
                  SCAN_LINE_TIME_NAME         :[0, 86400000],
                  CLOUD_FRACTION_NAME         :[0, 1],
                  LAND_FRACTION_NAME          :[0, 1],
                  RESULTS_FLAG_NAME           :[0, 3],
                  UTLS_FLAG_NAME              :[0, 2],
}

FILL_VALUES = {
                  CLOUD_TOP_PRESS_NAME        : -99.9,
                  CLOUD_TOP_HEIGHT_NAME       : -99.9,
                  CLOUD_TOP_TEMP_NAME         : -99.9,
                  EFFECTIVE_CLOUD_AMOUNT_NAME : -99.9,
                  METHOD_FLAG_NAME            : -99,
}

# the line between day and night for our day/night masks (in solar zenith angle degrees)
DAY_NIGHT_LINE_DEGREES = 84.0

def open_file (file_path) :
    """
    given a file path that is a modis file, open it
    """
    ctp_names = [
             LATITUDE_NAME              ,
             LONGITUDE_NAME             ,
             CLOUD_TOP_PRESS_NAME       ,
             CLOUD_TOP_HEIGHT_NAME      ,
             CLOUD_TOP_TEMP_NAME        ,
             EFFECTIVE_CLOUD_AMOUNT_NAME,
             METHOD_FLAG_NAME           ,
             DAY_NIGHT_FLAG_NAME        ,
             DIRECTION_FLAG_NAME        ,
             VIEWING_ZENITH_NAME        ,
             SCAN_LINE_TIME_NAME        ,
             CLOUD_FRACTION_NAME        ,
             LAND_FRACTION_NAME         ,
             RESULTS_FLAG_NAME          ,
             UTLS_FLAG_NAME             ,
    ]

    ctp_formats = ['(1100,56)f4'] * 15   # they're all the same

    ctp_type = numpy.dtype({'names' : ctp_names,
                            'formats' : ctp_formats})

    file_object = numpy.fromfile(file_path, dtype=ctp_type) # FIXME: will we have a problem from treating a numpy array as a file object? passing it around?

    return file_object

def close_file (file_object) :
    """
    given a file object, close it
    """
    del file_object


def load_aux_data (file_path, minimum_scan_angle, file_object=None) :
    """
    load the auxillary data and process the appropriate masks from it
    """
    
    # make our return structure
    aux_data_sets = { }
    
    # load the longitude and latitude
    file_object, aux_data_sets[LON_KEY] = load_variable_from_file (LONGITUDE_NAME,
                                                                   file_path=file_path, file_object=file_object)
    file_object, aux_data_sets[LAT_KEY] = load_variable_from_file (LATITUDE_NAME,
                                                                   file_path=file_path, file_object=file_object)
    
    # load the day/night flag to make day/night mask
    file_object, day_night_flag         = load_variable_from_file (DAY_NIGHT_FLAG_NAME,
                                                                   file_path=file_path, file_object=file_object)

    # build the day and night masks
    aux_data_sets[DAY_MASK_KEY]   = (day_night_flag == 1)
    aux_data_sets[NIGHT_MASK_KEY] = (day_night_flag == 2)
    
    return file_object, aux_data_sets

# FUTURE, the data type needs to be handled differently
def load_variable_from_file (variable_name, file_path=None, file_object=None,
                             fill_value_name=None,
                             scale_name=None,
                             offset_name=None,
                             data_type_for_output=numpy.float32) :
    """
    load a given variable from a file path or file object
    """
    if file_path is None and file_object is None :
        raise ValueError("File path or file object must be given to load file.")
    if file_object is None :
        file_object = open_file(file_path)

    data = file_object[variable_name]

    # Mask off fill values fill values
    if variable_name in FILL_VALUES:
      fill_value = FILL_VALUES[variable_name]
      data[data == fill_value] = numpy.nan

    # Mask off anything outside the valid range
    if variable_name in VALID_RANGES:
      valid_range = VALID_RANGES[variable_name]
      data[data < valid_range[0]] = numpy.nan
      data[data > valid_range[1]] = numpy.nan

    data_to_return = data.astype(data_type_for_output) if data_type_for_output is not None else data
    return file_object, data

# TODO, move this up to the general_guidebook
def _clean_off_path_if_needed(file_name_string) :
    """
    remove the path from the file if necessary
    """
    
    return os.path.basename(file_name_string)

def is_my_file (file_name_string) :
    """determine if a file name is the right pattern to represent a CTP file
    if the file_name_string matches how we expect CTP files to look return
    TRUE else will return FALSE
    """
    
    temp_name_string = _clean_off_path_if_needed(file_name_string)
    
    return (temp_name_string.endswith('ctp.bin'))

def parse_datetime_from_filename (file_name_string) :
    """parse the given file_name_string and create an appropriate datetime object
    that represents the datetime indicated by the file name; if the file name does
    not represent a pattern that is understood, None will be returned
    """
    
    temp_name_string = _clean_off_path_if_needed(file_name_string)

    temp = temp_name_string.split('.')
    datetime_to_return = datetime.strptime(temp[3] + temp[4], 'D%y%jS%H%M')

    return datetime_to_return

def get_satellite_from_filename (data_file_name_string) :
    """given a file name, figure out which satellite it's from
    if the file does not represent a known satellite name
    configuration None will be returned
    """
    
    temp_name_string = _clean_off_path_if_needed(data_file_name_string)
    temp = temp_name_string.split('.')

    SAT_LOOKUP = {'NK' : SAT_NOAA_15,
                  'NL' : SAT_NOAA_16,
                  'NM' : SAT_NOAA_17,
                  'NN' : SAT_NOAA_18,
                  'NP' : SAT_NOAA_19,
                  'NK' : SAT_NOAA_15,
                  'M2' : SAT_METOP_A, # yes, M2 really does = metop-a
                  'M1' : SAT_METOP_B,
    }

    satellite_to_return = SAT_LOOKUP[temp[3]]
    instrument_to_return = INST_HIRS

    return satellite_to_return, instrument_to_return

def get_variable_names (user_requested_names) :
    """get a list of variable names we expect to process from the file
    """
    
    var_names = set( )
    
    if len(user_requested_names) <= 0 :
        var_names.update(EXPECTED_VARIABLES_IN_FILE)
    else :

        for user_name in user_requested_names :
            if user_name in CALLER_VARIABLE_MAP.keys() :
                var_names.update(set([CALLER_VARIABLE_MAP[user_name]]))

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
