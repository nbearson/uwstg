#!/usr/bin/env python
# encoding: utf-8
"""
Provide information about products the system expects in CLAVRx files, how
they're stored in the files, and how to manage them during the process of
regridding.

:author:       Eva Schiffer (evas)
:contact:      evas@ssec.wisc.edu
:organization: Space Science and Engineering Center (SSEC)
:copyright:    Copyright (c) 2014 University of Wisconsin SSEC. All rights reserved.
:date:         Jan 2014
:license:      GNU GPLv3
:revision:     $Id$
"""
__docformat__ = "restructuredtext en"

from stg.constants import *

from pyhdf.SD import SD,SDC, SDS, HDF4Error

import sys
import os
import logging
import numpy
from datetime import datetime

LOG = logging.getLogger(__name__)


# variable names expected in the files

#GEO:
LATITUDE_NAME               = 'latitude'
LONGITUDE_NAME              = 'longitude'
SOLAR_ZENITH_NAME           = 'solar_zenith_angle'
SENSOR_ZENITH_NAME          = 'sensor_zenith_angle'

#PRODUCTS:
CLOUD_MASK_NAME             = 'cloud_mask'
CLOUD_HEIGHT_NAME           = 'cloud_type'
CLOUD_TYPE_NAME             = 'cld_height_acha'


# important attribute names
SCALE_ATTR_NAME             = 'scale_factor'
ADD_OFFSET_ATTR_NAME        = 'add_offset'
FILL_VALUE_ATTR_NAME        = '_fillvalue'

# a map of what the caller calls variables to variable names in files
CALLER_VARIABLE_MAP     = {
                            'latitude':                     LATITUDE_NAME,
                            'lat':                          LATITUDE_NAME,
                            
                            'longitude':                    LONGITUDE_NAME,
                            'lon':                          LONGITUDE_NAME,
                            
                            'solar zenith':                 SOLAR_ZENITH_NAME,
                            'sunzen':                       SOLAR_ZENITH_NAME,
                            
                            'sensor zenith':                SENSOR_ZENITH_NAME,
                            'satzen':                       SENSOR_ZENITH_NAME,
                            'viewing zenith':               SENSOR_ZENITH_NAME,

                            'cloud mask':      CLOUD_MASK_NAME,
                            'cloud height':    CLOUD_HEIGHT_NAME,
                            'cloud type':      CLOUD_TYPE_NAME,
                          }

DATA_TYPE_TO_USE = { # TODO, eventually differentiate the data type by variable
                    LATITUDE_NAME:                  numpy.float32,
                    LONGITUDE_NAME:                 numpy.float32,
                    SOLAR_ZENITH_NAME:              numpy.float32,
                    SENSOR_ZENITH_NAME:             numpy.float32,
                    CLOUD_MASK_NAME   : numpy.int8,
                    CLOUD_HEIGHT_NAME : numpy.float32,
                    CLOUD_TYPE_NAME   : numpy.int8,
                   }

# a list of the default variables expected in a file, used when no variables are selected by the caller
EXPECTED_VARIABLES_IN_FILE = set([CLOUD_MASK_NAME]) # TODO, this is currently set for our minimal testing

# the line between day and night for our day/night masks (in solar zenith angle degrees)
DAY_NIGHT_LINE_DEGREES = 84.0

def open_file (file_path) :
    """
    given a file path that is a modis file, open it
    """

    file_object = SD(file_path, SDC.READ)

    return file_object

def close_file (file_object) :
    """
    given a file object, close it
    """

    file_object.end()

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

    # load the angles to make masks
    file_object, solar_zenith_data_temp = load_variable_from_file (SOLAR_ZENITH_NAME,
                                                                   file_path=file_path, file_object=file_object)
    file_object, sat_zenith_data_temp   = load_variable_from_file (SENSOR_ZENITH_NAME,
                                                                   file_path=file_path, file_object=file_object)

    # transform the satellite zenith to scan angle
    scan_angle_data_temp = _satellite_zenith_angle_to_scan_angle(sat_zenith_data_temp)

    # build the day and night masks
    ok_scan_angle                 =  scan_angle_data_temp   <= minimum_scan_angle
    aux_data_sets[DAY_MASK_KEY]   = (solar_zenith_data_temp <  DAY_NIGHT_LINE_DEGREES) & ok_scan_angle
    aux_data_sets[NIGHT_MASK_KEY] = (solar_zenith_data_temp >= DAY_NIGHT_LINE_DEGREES) & ok_scan_angle

    return file_object, aux_data_sets

# FUTURE, the data type needs to be handled differently
def load_variable_from_file (variable_name, file_path=None, file_object=None,
                             fill_value_name=FILL_VALUE_ATTR_NAME,
                             scale_name=SCALE_ATTR_NAME,
                             offset_name=ADD_OFFSET_ATTR_NAME,
                             data_type_for_output=numpy.float32) :
    """
    load a given variable from a file path or file object
    """

    if file_path is None and file_object is None :
        raise ValueError("File path or file object must be given to load file.")
    if file_object is None :
        file_object = open_file(file_path)

    variable_names = file_object.datasets().keys()
    if variable_name not in variable_names :
        raise ValueError("Variable " + str(variable_name) +
                         " is not present in file " + str(file_path) + " .")

    # defaults
    scale_factor = 1.0
    add_offset = 0.0
    data_type = None

    # get the variable object and use it to
    # get our raw data and scaling info
    variable_object = file_object.select(variable_name)
    raw_data_copy   = variable_object[:]
    raw_data_copy   = raw_data_copy.astype(data_type_for_output) if data_type_for_output is not None else raw_data_copy
    temp_attrs      = variable_object.attributes()
    try :
        scale_factor, scale_factor_error, add_offset, add_offset_error, data_type = SDS.getcal(variable_object)
    except HDF4Error:
        # load just the scale factor and add offset information by hand
        if offset_name in temp_attrs.keys() :
            add_offset = temp_attrs[offset_name]
            data_type = numpy.dtype(type(add_offset))
        if scale_name in temp_attrs.keys() :
            scale_factor = temp_attrs[scale_name]
            data_type = numpy.dtype(type(scale_factor))

    # get the fill value
    fill_value = temp_attrs[fill_value_name] if fill_value_name in temp_attrs.keys() else numpy.nan
    # change the fill value to numpy.nan
    fill_mask = raw_data_copy == fill_value
    if fill_value is not numpy.nan :
        raw_data_copy[fill_mask] = numpy.nan
        fill_value = numpy.nan

    # we got all the info we need about that file
    SDS.endaccess(variable_object)

    # don't do lots of work if we don't need to scale things
    if (scale_factor == 1.0) and (add_offset == 0.0) :
        return file_object, raw_data_copy

    # if we don't have a data type something strange has gone wrong
    assert(data_type is not None)

    # create the scaled version of the data
    scaled_data_copy                = raw_data_copy.copy()
    scaled_data_copy = unscale_data(scaled_data_copy, fill_mask=fill_mask,
                                    scale_factor=scale_factor, offset=add_offset)

    return file_object, scaled_data_copy

def unscale_data (data, fill_mask=None, scale_factor=None, offset=None) :
    """unscale the given data

    data is modified in place and fill values will not be changed
    if a scale factor or offset is given as None (or not given) it will not be applied

    the general formula for unscaling data is:

            final_data = (input_data * scale_factor) + offset
    """

    to_return = data

    not_fill_mask = ~fill_mask

    # if we found a scale use it to scale the data
    if (scale_factor is not None) and (scale_factor is not 1.0) :
        to_return[not_fill_mask] *= scale_factor

    # if we have an offset use it to offset the data
    if (offset is       not None) and (offset       is not 0.0) :
        to_return[not_fill_mask] += offset

    return to_return


# FUTURE, will this be used for other satellites? should it move up to the io_manager?
def _satellite_zenith_angle_to_scan_angle (sat_zenith_data) :
    """
    given a set of satellite zenith angles, calculate the equivalent scan angles

    Note: This comes directly from Nadia's satz2scang function.
    """

    # some constants
    re = 6371.03;
    altkm = 825;
    fac = re / (re + altkm);
    dtr = 0.01745329;

    # do the angle calculations
    arg_data        = sat_zenith_data * dtr
    ang_data        = numpy.sin(numpy.sin(arg_data) * fac)
    scan_angle_data = ang_data / dtr

    return scan_angle_data


# TODO, move this up to the general_guidebook
def _clean_off_path_if_needed(file_name_string) :
    """
    remove the path from the file if nessicary
    """
    
    return os.path.basename(file_name_string)

def is_my_file (file_name_string) :
    """determine if a file name is the right pattern to represent a CLAVRx file
    if the file_name_string matches how we expect CLAVRx files to look return
    TRUE else will return FALSE
    """
    
    temp_name_string = _clean_off_path_if_needed(file_name_string)
    
    return (temp_name_string.startswith('CLAVRx') and temp_name_string.endswith('hdf'))

def parse_datetime_from_filename (file_name_string) :
    """parse the given file_name_string and create an appropriate datetime object
    that represents the datetime indicated by the file name; if the file name does
    not represent a pattern that is understood, None will be returned
    """
    
    temp_name_string = _clean_off_path_if_needed(file_name_string)
    
    datetime_to_return = None
    
    temp = temp_name_string.split('.')
    datetime_to_return = datetime.strptime(temp[2] + temp[3], "%y%j%H%M")

    return datetime_to_return

def get_satellite_from_filename (data_file_name_string) :
    """given a file name, figure out which satellite it's from
    if the file does not represent a known satellite name
    configuration None will be returned
    """
    
    temp_name_string = _clean_off_path_if_needed(data_file_name_string)
    
    temp = temp_name_string.split('.')
    if temp[1] == "a1":
      satellite_to_return = SAT_AQUA
      instrument_to_return = INST_MODIS
    elif temp[1] == "t1":
      satellite_to_return = SAT_TERRA
      instrument_to_return = INST_MODIS
    else:
      raise NotImplementedError

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
