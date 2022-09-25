#!/usr/bin/env python3

#rm ${HOME}/.cache/gstreamer-1.0/registry.aarch64.bin    borrar cache
################################################################################
# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
################################################################################
#
#   version 2.1 solo identificara personas y carros sin ninguna caracteristica 
#   adicional,se realiza eliminando las clases de carro, bicicleta y senal de 
#   transito con el parametro filter-out-class-ids=0;1;3 en el archivo dstest2_pgie_config.txt
#
################################################################################
import sys
import os
import re
sys.path.append('../')
import platform
import configparser

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
from common.FPS import GETFPS

import pyds
import services as service

#Bibliotecas Adicioanles para la funcionaliad con Tiler
from gi.repository import GLib
from ctypes import *
import time
import math
import datetime

import json


#################################
import lib.biblioteca as biblio
import lib.server as srv
import lib.common as com
import lib.validate as vl
#################################


#
#  version 2.1 solo detectara personas
#  sin embargo la logica del programa permite 
#  seguir contando otras clases si asi se 
#  requiriera
#  
# 11-nov-2021
# Esta version solo detectara personas
# todo lo demás se elimina 

#PGIE_CLASS_ID_VEHICLE = 0
#PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 0                    # si se ocupa Peoplenet la clase es 0 personas, bolsas 1 y rostros 2
#PGIE_CLASS_ID_PERSON = 2
#PGIE_CLASS_ID_ROADSIGN = 3

#PEOPLE_COUNTING_SERVICE = 0
#AFORO_ENT_SAL_SERVICE = 1
#SOCIAL_DISTANCE_SERVICE = 2

#
# Variables adicionales para el manejo de la funcionalidad de Tiler
# independientemente como venga los parametros del video se ajusta 
# a los parametros del muxer
#

MAX_DISPLAY_LEN = 64
MUXER_OUTPUT_WIDTH = 1920
MUXER_OUTPUT_HEIGHT = 1080
MUXER_BATCH_TIMEOUT_USEC = 4000000
TILED_OUTPUT_WIDTH = 1920
TILED_OUTPUT_HEIGHT = 1080
GST_CAPS_FEATURES_NVMM = "memory:NVMM"

#pgie_classes_str = ["Vehicle", "TwoWheeler", "Person", "RoadSign"]

# directorio actual
CURRENT_DIR = os.getcwd()

# Matriz de frames per second, Se utiliza en tiler
fps_streams = {}


#Stores actions to execute per camera, each camera can execute multiple services
#the only condition is all are based on the same model
global action
action = {}

# the the path or video source to use, this value is 
# unique per camera even though the source is a recorded mp4
global sources
sources = {}

# stores header for the server communication exchange
global header
header = None

# stores the path of the toke for the server communication exchange
global token_file
token_file = None

# stores the configuration within all its process from reading, filtering
# valiating values and add new parameters and format values. 
global scfg
scfg = {}

# stores the order of how the sources are executed and associates an id
# so that we can all it in the tiler function for the specific services
global call_order_of_keys
call_order_of_keys = []

# store global frame counting 
frame_count = {}
saved_count = {}


########## AFORO ##########
# stores the configuration parameters and values of all the defined 
# aforo's services (counting in/out people service). Only 1 aforo 
# service per camera 
global aforo_list
aforo_list = {}

global entradas_salidas
entradas_salidas = {}

global initial_last_disappeared
initial_last_disappeared = {}


########## SOCIAL DISTANCE ##########
global social_distance_list
social_distance_list = {}
global social_distance_url
global social_distance_ids
social_distance_ids = {}


########## PEOPLE COUNTING ##########
global people_counting_url
global people_counting_counters
people_counting_counters = {}
global people_distance_list
people_distance_list = {}


#################  Model and service functions  #################

def set_header(token_file=None):
    if token_file is None:
        token_file = os.environ['TOKEN_FILE']

    if com.file_exists(token_file):
        global header
        token_handler = com.open_file(token_file, 'r+')
        header = {'Content-type': 'application/json', 'X-KAIROS-TOKEN': token_handler.read().split('\n')[0]}
        com.log_debug('Header correctly set')
        return header
    com.log_error('Unable to read token')

##############################################################


def set_initial_last_disappeared(key_id):
    global initial_last_disappeared

    if key_id not in initial_last_disappeared:
        initial_last_disappeared.update({key_id: [{}, {}, []]})

    set_entrada_salida(key_id, 0, 0)


def get_initial_last(key_id):
    global initial_last_disappeared

    if key_id in initial_last_disappeared:
        return initial_last_disappeared[key_id][0], initial_last_disappeared[key_id][1]


def set_disappeared(key_id, value = None):
    global initial_last_disappeared

    if value is None:
        initial_last_disappeared[key_id][2] = []
    else:
        initial_last_disappeared[key_id][2] = value


def get_disappeared(key_id):
    global initial_last_disappeared

    if key_id in initial_last_disappeared:
        return initial_last_disappeared[key_id][2]
    return None


def get_people_counting_counter(key_id):
    global people_counting_counters

    if key_id and key_id in people_counting_counters.keys():
        return people_counting_counters[key_id]


def set_people_counting_counter(key_id, value):
    global people_counting_counters

    if key_id is not None and isinstance(value, int) and value > -1:
        people_counting_counters.update({key_id: value})


def set_people_counting(key_id, people_couting_data):
    global people_distance_list

    if not isinstance(people_couting_data, dict):
        service.log_error("'people_counting_data' parameter, most be a dictionary")

    if not isinstance(people_couting_data['enabled'], bool) :
        service.log_error("'people_counting_data' parameter, most be True or False")

    people_distance_list[key_id] = people_couting_data
    set_people_counting_counter(key_id, 0)


def set_social_distance(key_id, social_distance_data):
    global social_distance_list

    if not isinstance(social_distance_data, dict):
        service.log_error("'social_distance_data' parameter, most be a dictionary")

    if not isinstance(social_distance_data['enabled'], bool):
        service.log_error("'social_distance_data' parameter, most be True or False")

    if not isinstance(int(float(social_distance_data['tolerated_distance'])), int) and int(float(social_distance_data['tolerated_distance'])) > 3:
        service.log_error("'social_distance_data.tolarated_distance' parameter, most be and integer bigger than 3 pixels")
    else:
        new_value = int(float(social_distance_data['tolerated_distance']))
        social_distance_data.update({'tolerated_distance': new_value})

    if not isinstance(int(float(social_distance_data['persistence_time'])), int) and int(float(social_distance_data['persistence_time'])) > -1:
        service.log_error("'social_distance_data.persistence_time' parameter, most be a positive integer/floater")
    else:
        new_value = int(float(social_distance_data['persistence_time'])) * 1000
        social_distance_data.update({'tolerated_distance': new_value})

    #social_distance_data.update({'persistence_time': social_distance_data['persistence_time'] * 1000})

    social_distance_list.update(
            {
                key_id: social_distance_data
            })

    social_distance_list[key_id].update({'social_distance_ids': {}})


def get_people_counting(key_id):
    global people_distance_list

    if key_id not in people_distance_list.keys():
        return {'enabled': False}

    return people_distance_list[key_id]


def get_social_distance(key_id, key = None):
    global social_distance_list

    if key_id not in social_distance_list.keys():
        return {'enabled': False}

    if social_distance_list:
        if key:
            return social_distance_list[key_id][key]
        else:
            return social_distance_list[key_id]


def get_aforo(camera_id, key = None, second_key = None):
    global aforo_list

    if camera_id not in aforo_list:
        return {'enabled': False}

    if key is None:
        return aforo_list[camera_id]
    else:
        if second_key is None:
            return aforo_list[camera_id][key]
        else:
            return aforo_list[camera_id][key][second_key]


def set_sources(srv_camera_service_id, source_value):
    global sources

    if srv_camera_service_id not in sources:
        sources.update({srv_camera_service_id: source_value})
    else:
        source[srv_camera_service_id] = source_value


def get_sources():
    global sources
    return sources


def get_camera_id(index):
    global call_order_of_keys
    return call_order_of_keys[index]


def set_token(token_file_name):
    if isinstance(token_file_name, str) and service.file_exists(token_file_name):
        global token_file
        token_file = token_file_name
        return True
    service.log_error("'token_file_name={}' parameter, most be a valid string".format(token_file_name))


def set_entrada_salida(key_id, entrada, salida):
    global entradas_salidas

    if key_id not in entradas_salidas:
        entradas_salidas.update({key_id: [entrada, salida]})
    else:
        entradas_salidas[key_id] = [entrada, salida]


def get_entrada_salida(key_id):
    global entradas_salidas

    if key_id not in entradas_salidas:
        return 0, 0
    return entradas_salidas[key_id][0], entradas_salidas[key_id][1]


def validate_keys(service, data, list_of_keys):

    if not isinstance(data, dict):
        service.log_error("'data' parameter, most be a dictionary")
    if 'enabled' not in data:
        return False

    for key in data.keys():
        if key == 'enabled' and data[key] == 'False':
            return False

    for key in list_of_keys:
        if key not in data.keys():
            service.log_error("'{}' missing parameter {}, in config file".format(service, key))

    return True


def get_dictionary_from_list(srv_id):
    global scfg

    camera_mac = srv_id.split('_')[1]
    for dict_element in scfg[camera_mac]['services']:
        if srv_id in dict_element:
            return dict_element[srv_id]

    com.log_error("Unable to find the key: "+key_to_search+" in the data")


def validate_aforo_values(data, srv_id, service_name):
    aforo_dict = get_dictionary_from_list(srv_id)['aforo']

    if 'endpoint' not in aforo_dict:
        service.log_error("Missing parameter 'endpoint' for service Aforo")
    else:
        if not isinstance(aforo_dict['endpoint'], str):
            service.log_error("Parameter 'endpoint' most be string")

    if 'reference_line' not in aforo_dict:
        service.log_error("Missing parameter 'reference_line' for service Aforo")
    else:
        if not isinstance(aforo_dict['reference_line'], dict):
            service.log_error("reference_line, most be a directory")

        if 'line_coordinates' not in aforo_dict['reference_line']:
            service.log_error("line_coordinates, not defined")

        if not isinstance(aforo_dict['reference_line']['line_coordinates'], list):
            service.log_error("line_coordinates, should be a list")
            
        for coordinate in aforo_dict['reference_line']['line_coordinates']:
            if not isinstance(coordinate,list):
                service.log_error("line_coordinates, elements should be list type")
            if len(coordinate) != 2:
                service.log_error("line_coordinates, every element is a list representing a coordinates in the layer x,y")
            for element in coordinate:
                if not isinstance(element, int):
                    service.log_error("line_coordinates, every coordinates x,y should be an integer - {}".format(type(element)))
                if element < 0:
                    service.log_error("line_coordinates, every coordinates x,y should be an integer positive: {}".format(element))

        if 'outside_area' not in aforo_dict['reference_line']:
            service.log_error("'outside_area' must be defined as part of the reference_line values")

        if not isinstance(aforo_dict['reference_line']['outside_area'], int):
            service.log_error("outside_area should be integer")

        if aforo_dict['reference_line']['outside_area'] not in [1,2]:
            service.log_error("outside_area value most 1 or 2")

        if 'line_width' not in aforo_dict['reference_line']:
            default_witdth = 3
            aforo_dict['reference_line']['line_width'] = default_witdth;
            com.log_debug("Parameter 'line_color' was not defined. Using default value: "+str(default_witdth))

        if 'line_color' not in aforo_dict['reference_line']:
            default_color = [222,221,100,99]
            aforo_dict['reference_line']['line_color'] = default_color;
            com.log_debug("Parameter 'line_color' was not defined. Using default value: "+default_color)

    for color in aforo_dict['reference_line']['line_color']:
        try:
            color_int = int(color)
        except Exception as e:
            service.log_error("color values should be integers within 0-255")
        if color_int < 0 or color_int > 255:
            service.log_error("color values should be integers within 0-255")

    if 'area_of_interest' in aforo_dict:
        for key in aforo_dict['area_of_interest']:
            try:
                element_int = int(aforo_dict['area_of_interest'][key])
            except ValueError:
                com.log_error("Value of parameter: '{}' should be integer: {}".format(key), aforo_dict['area_of_interest'][key])

            if element_int < 0:
                com.log_error("Value of parameter: '{}' should be integer positive - {}".format(key, element_int))

        for parameter in ['padding_right', 'padding_left', 'padding_top', 'padding_bottom']:
            if parameter not in aforo_dict['area_of_interest']:
                aforo_dict['area_of_interest'][parameter] = 0


def validate_socialdist_values(data):

    #print('print1', data, '...', ['enabled', 'tolerated_distance', 'persistence_time'])
    if not validate_keys('video-socialDistancing', data, ['enabled', 'tolerated_distance', 'persistence_time']):
        return False

    if not isinstance(data['enabled'], str):
        service.log_error("'enabled' parameter, most be string: {}".format(data['enabled']))
    
    if not isinstance(float(data['tolerated_distance']), float) and float(data['tolerated_distance']) > 0:
        service.log_error("tolerated_distance element, most be a positive integer")
    else:
        data.update({'tolerated_distance': float(data['tolerated_distance'])})

    if not isinstance(float(data['persistence_time']), float)  and float(data['persistence_time']) > 0:
        service.log_error("persistence_time element, most a be positive integer/floater")
    else:
        data.update({'persistence_time': float(data['persistence_time'])})

    return True


def validate_people_counting_values(data):

    validate_keys('people_counting', data, ['enabled'])

    if not isinstance(data['enabled'], bool):
        service.log_error("'people_counting.' parameter, most be True or False, current value: {}".format(data['enabled']))

    return True


def set_aforo(scfg, srv_camera_id, service_name):
    # use aforo_list for aforo
    global aforo_list

    camera_mac = srv_camera_id[7:24]
    data = {}
    for service_definition in scfg[camera_mac]['services']:
        if srv_camera_id in service_definition and service_name in service_definition[srv_camera_id]:
            data = service_definition[srv_camera_id][service_name]

    # Copia de los datos de configuracion de aforo
    aforo_list.update({camera_mac: data})

    if 'reference_line' in data and 'area_of_interest' in data:
        x1 = data['reference_line']['line_coordinates'][0][0]
        y1 = data['reference_line']['line_coordinates'][0][1]
        x2 = data['reference_line']['line_coordinates'][1][0]
        y2 = data['reference_line']['line_coordinates'][1][1]

        # padding es un espacio entre la linea y los bordes del area
        # si no se define es por default 0
        padding_left = data['area_of_interest']['padding_left']
        padding_top = data['area_of_interest']['padding_top']
        padding_right = data['area_of_interest']['padding_right']
        padding_bottom = data['area_of_interest']['padding_bottom']

        if x1 < x2:
            topx = x1 - padding_left
            width = abs((x2 + padding_right + padding_left) - x1)
        else:
            topx = x2 - padding_left
            width = abs((x1 + padding_right + padding_left) - x2)

        # adjusting if value is negative
        if topx < 0:
            topx = 1

        if y1 < y2:
            topy = y1 - padding_top
            height = abs((y2 + padding_bottom + padding_top) - y1)
        else:
            topy = y2 - padding_top
            height = abs((y1 + padding_bottom + padding_top) - y2)

        # adjusting if value is negative
        if topy < 0:
            topy = 0

        # ecuacion de la pendiente
        if (x2 - x1) == 0:
            m = None
            b = None
        elif (y2 - y1) == 0:
            m = 0
            b = 0
        else:
            m = ((y2 - y1) * 1.0) / (x2 -x1)
            b = y1 - (m * x1)

        if 'line_width' not in data['reference_line']:
            data['reference_line']['line_width'] = 2

        aforo_list[camera_mac].update({'line_m_b': [m, b]})
        aforo_list[camera_mac]['area_of_interest'].update({'area_rectangle': [topx, topy, width, height]})
        aforo_list[camera_mac]['endpoint'] = scfg[camera_mac]['server_url']+aforo_list[camera_mac]['endpoint']
    else:
        service.log_error("Missing configuration parameters for 'aforo' service")


def set_service_people_counting_url(server_url):
    global people_counting_url
    people_counting_url = server_url + 'SERVICE_NOT_DEFINED_'
    return people_counting_url


def get_service_people_counting_url():
    global people_counting_url
    return people_counting_url


def set_social_distance_url(server_url):
    global social_distance_url
    social_distance_url = server_url + 'tx/video-socialDistancing.endpoint'
    return social_distance_url


def get_social_distance_url():
    global social_distance_url
    return social_distance_url


def tiler_src_pad_buffer_probe(pad, info, u_data):
    # Intiallizing object counter with 0.
    # version 2.1 solo personas
    global header

    obj_counter = {
            PGIE_CLASS_ID_PERSON: 0
            }

    #PGIE_CLASS_ID_VEHICLE: 0,
    #PGIE_CLASS_ID_BICYCLE: 0,
    #PGIE_CLASS_ID_ROADSIGN: 0
    
    frame_number = 0
    num_rects = 0                      # numero de objetos en el frame
    gst_buffer = info.get_buffer()

    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    #====================== Definicion de valores de mensajes a pantalla
    display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
    current_pad_index = pyds.NvDsFrameMeta.cast(l_frame.data).pad_index

    camera_id = get_camera_id(current_pad_index)

    aforo_info = get_aforo(camera_id) 
    is_aforo_enabled = aforo_info['enabled']

    social_distance_info = get_social_distance(camera_id)
    is_social_distance_enabled = social_distance_info['enabled']

    people_counting_info = get_people_counting(camera_id)
    is_people_counting_enabled = people_counting_info['enabled']

    # Todos los servicios requieren impresion de texto solo para Aforo se requiere una linea y un rectangulo
    display_meta.num_labels = 1                            # numero de textos
    py_nvosd_text_params = display_meta.text_params[0]

    # Setup del label de impresion en pantalla
    py_nvosd_text_params.x_offset = 1200
    py_nvosd_text_params.y_offset = 100
    py_nvosd_text_params.font_params.font_name = "Arial"
    py_nvosd_text_params.font_params.font_size = 20
    py_nvosd_text_params.font_params.font_color.red = 1.0
    py_nvosd_text_params.font_params.font_color.green = 1.0
    py_nvosd_text_params.font_params.font_color.blue = 1.0
    py_nvosd_text_params.font_params.font_color.alpha = 1.0
    py_nvosd_text_params.set_bg_clr = 1
    py_nvosd_text_params.text_bg_clr.red = 0.0
    py_nvosd_text_params.text_bg_clr.green = 0.0
    py_nvosd_text_params.text_bg_clr.blue = 0.0
    py_nvosd_text_params.text_bg_clr.alpha = 1.0

    if is_aforo_enabled:
        reference_line = aforo_info['reference_line']['line_coordinates']

        #------------------------------------------- display info
        display_meta.num_lines = 1      # numero de lineas
        display_meta.num_rects = 1      # numero de rectangulos  
        py_nvosd_line_params = display_meta.line_params[0]                
        py_nvosd_rect_params = display_meta.rect_params[0]        

        # Setup de la linea de Ent/Sal
        # los valos de las coordenadas tienen que ser obtenidos del archivo de configuracion
        # en este momento estan hardcode

        if reference_line:
            aforo_line_color = aforo_info['reference_line']['line_color']
            outside_area = aforo_info['reference_line']['outside_area']
            py_nvosd_line_params.x1 = reference_line[0][0]
            py_nvosd_line_params.y1 = reference_line[0][1]
            py_nvosd_line_params.x2 = reference_line[1][0]
            py_nvosd_line_params.y2 = reference_line[1][1]
            py_nvosd_line_params.line_width = aforo_info['reference_line']['line_width']
            py_nvosd_line_params.line_color.red = aforo_line_color[0]
            py_nvosd_line_params.line_color.green = aforo_line_color[1]
            py_nvosd_line_params.line_color.blue = aforo_line_color[2]
            py_nvosd_line_params.line_color.alpha = aforo_line_color[3]
        else:
            outside_area = None

        if aforo_info['area_of_interest']['area_rectangle']:
            '''
            # setup del rectangulo de Ent/Sal                        #TopLeftx, TopLefty --------------------
            # de igual manera que los parametros de linea,           |                                      |
            # los valores del rectangulo se calculan en base a       |                                      |
            # los valoes del archivo de configuracion                v                                      |
            #                                                        #Height -------------------------> Width
            '''

            TopLeftx = aforo_info['area_of_interest']['area_rectangle'][0]
            TopLefty = aforo_info['area_of_interest']['area_rectangle'][1]
            Width = aforo_info['area_of_interest']['area_rectangle'][2]
            Height = aforo_info['area_of_interest']['area_rectangle'][3]
            x_plus_width = TopLeftx + Width
            y_plus_height = TopLefty + Height

            rectangle = [TopLeftx, TopLefty, Width, Height, x_plus_width, y_plus_height]

            py_nvosd_rect_params.left = TopLeftx
            py_nvosd_rect_params.height = Height
            py_nvosd_rect_params.top = TopLefty
            py_nvosd_rect_params.width = Width

            py_nvosd_rect_params.border_width = 4
            py_nvosd_rect_params.border_color.red = 0.0
            py_nvosd_rect_params.border_color.green = 0.0
            py_nvosd_rect_params.border_color.blue = 1.0
            py_nvosd_rect_params.border_color.alpha = 1.0

    if is_social_distance_enabled:
        persistence_time = social_distance_info['persistence_time']
        tolerated_distance = social_distance_info['tolerated_distance']
        max_side_plus_side = tolerated_distance * 1.42
        detected_ids = social_distance_info['social_distance_ids']
        #risk_value = nfps * persistence_time # TODO esta valor no se necesitara en al version 3.2

    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        #print(" fps:",frame_meta.num_surface_per_frame)
        l_obj = frame_meta.obj_meta_list
        num_rects = frame_meta.num_obj_meta
        
        #print(num_rects) ID numero de stream
        ids = []
        boxes = []
        ids_and_boxes = {}

        # Ciclo interno donde se evaluan los objetos dentro del frame
        while l_obj is not None: 
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)         
            except StopIteration:
                break           

            x = obj_meta.rect_params.width
            y = obj_meta.rect_params.height
            t = obj_meta.rect_params.top
            l = obj_meta.rect_params.left
         
            #print(" width-x height -y Top  LEft ", x, "  ",y,"  ",t,"   ",l)
            obj_counter[obj_meta.class_id] += 1
            ids.append(obj_meta.object_id)
            x = int(obj_meta.rect_params.left + obj_meta.rect_params.width/2)

            if is_social_distance_enabled:
                # centroide al pie
                y = int(obj_meta.rect_params.top + obj_meta.rect_params.height) 
                ids_and_boxes.update({obj_meta.object_id: (x, y)})

            # Service Aforo (in and out)
            if is_aforo_enabled:
                # centroide al hombligo
                y = int(obj_meta.rect_params.top + obj_meta.rect_params.height/2) 
                boxes.append((x, y))

                if aforo_info['area_of_interest']['area_rectangle']:
                    entrada, salida = get_entrada_salida(camera_id)
                    initial, last = get_initial_last(camera_id)
                    entrada, salida = service.aforo(aforo_info['endpoint'], (x, y), obj_meta.object_id, ids, camera_id, initial, last, entrada, salida, outside_area, reference_line, aforo_info['line_m_b'][0], aforo_info['line_m_b'][1], rectangle)
                    set_entrada_salida(camera_id, entrada, salida)
                else:
                    '''
                    not fully implemented - complex polygons of 3 or more than 4 sides
                    '''
                    #aa = service.is_point_inside_polygon(x, y, polygon_sides, polygon)
                    entrada, salida = get_entrada_salida(camera_id)
                    initial, last = get_initial_last(camera_id)
                    entrada, salida = service.aforo(header, aforo_info['endpoint'], (x, y), obj_meta.object_id, ids, camera_id, initial, last, entrada, salida, outside_area, reference_line, aforo_info['line_m_b'][0], aforo_info['line_m_b'][1])
                    set_entrada_salida(camera_id, entrada, salida)
            try: 
                l_obj = l_obj.next
            except StopIteration:
                break

        if is_aforo_enabled:
            entrada, salida = get_entrada_salida(camera_id)
            py_nvosd_text_params.display_text = "AFORO Total persons={} Entradas={} Salidas={}".format(obj_counter[PGIE_CLASS_ID_PERSON], entrada, salida)
            #py_nvosd_text_params.display_text = "AFORO Source ID={} Source={} Total persons={} Entradas={} Salidas={}".format(frame_meta.source_id, frame_meta.pad_index , obj_counter[PGIE_CLASS_ID_PERSON], entrada, salida)

            '''
            Este bloque limpia los dictionarios initial y last, recolectando los ID que 
            no ya estan en la lista actual, es decir, "candidatos a ser borrados" y 
            despues es una segunda corroboracion borrandolos
            15 se elige como valor maximo en el cual un id puede desaparecer, es decir, si un id desaparece por 15 frames, no esperamos
            recuperarlo ya
            '''
            if frame_number > 0 and frame_number % 159997967 == 0:
                disappeared = get_disappeared(camera_id)
                initial, last = get_initial_last(camera_id)
                if disappeared:
                    elements_to_be_delete = [ key for key in last.keys() if key not in ids and key in disappeared ]
                    for x in elements_to_be_delete:
                        last.pop(x)
                        initial.pop(x)
                    set_disappeared(camera_id)
                else:
                    elements_to_be_delete = [ key for key in last.keys() if key not in ids ]
                    set_disappeared(camera_id, elements_to_be_delete)

        if is_social_distance_enabled:
            if len(ids_and_boxes) > 1: # if only 1 object is present there is no need to calculate the distance
                service.social_distance2(get_social_distance_url(), camera_id, ids_and_boxes, tolerated_distance, persistence_time, max_side_plus_side, detected_ids)
            py_nvosd_text_params.display_text = "SOCIAL DISTANCE Source ID={} Source Number={} Person_count={} ".format(frame_meta.source_id, frame_meta.pad_index , obj_counter[PGIE_CLASS_ID_PERSON])

        if is_people_counting_enabled:
            if obj_counter[PGIE_CLASS_ID_PERSON] != get_people_counting_counter(camera_id):
                #print(camera_id, ' anterior, actual:',get_people_counting_counter(camera_id), obj_counter[PGIE_CLASS_ID_PERSON])
                set_people_counting_counter(camera_id, obj_counter[PGIE_CLASS_ID_PERSON])
                service.people_counting(camera_id, obj_counter[PGIE_CLASS_ID_PERSON])

        #====================== FIN de definicion de valores de mensajes a pantalla

        # Lo manda a directo streaming
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)

        fps_streams["stream{0}".format(frame_meta.pad_index)].get_fps()       
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK	


def cb_newpad(decodebin, decoder_src_pad, data):
    print("In cb_newpad\n")
    caps = decoder_src_pad.get_current_caps()
    gststruct = caps.get_structure(0)
    gstname = gststruct.get_name()
    source_bin = data
    features = caps.get_features(0)

    # Need to check if the pad created by the decodebin is for video and not audio.
    print("gstname=", gstname)
    if gstname.find("video") != -1:
        # Link the decodebin pad only if decodebin has picked nvidia
        # decoder plugin nvdec_*. We do this by checking if the pad caps contain
        # NVMM memory features.
        print("features=", features)
        if features.contains("memory:NVMM"):
            # Get the source bin ghost pad
            bin_ghost_pad = source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")


def decodebin_child_added(child_proxy, Object, name, user_data):
    print("Decodebin child added:", name, "\n")
    if name.find("decodebin") != -1:
        Object.connect("child-added", decodebin_child_added, user_data)
    if is_aarch64() and name.find("nvv4l2decoder") != -1:
        print("Seting bufapi_version\n")
        Object.set_property("bufapi-version", True)


def create_source_bin(index, uri):
    print("Creating source bin")

    # Create a source GstBin to abstract this bin's content from the rest of the pipeline
    bin_name = "source-bin-%02d" % index
    nbin = Gst.Bin.new(bin_name)
    if not nbin:
        sys.stderr.write(" Unable to create source bin \n")

    # Source element for reading from the uri.
    # We will use decodebin and let it figure out the container format of the
    # stream and the codec and plug the appropriate demux and decode plugins.
    uri_decode_bin = Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
    if not uri_decode_bin:
        sys.stderr.write(" Unable to create uri decode bin \n")
    # We set the input uri to the source element
    uri_decode_bin.set_property("uri", uri)
    uri_decode_bin.connect("pad-added", cb_newpad, nbin)
    uri_decode_bin.connect("child-added", decodebin_child_added, nbin)

    Gst.Bin.add(nbin, uri_decode_bin)
    bin_pad = nbin.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))
    if not bin_pad:
        sys.stderr.write(" Failed to add ghost pad in source bin \n")
        return None
    return nbin


def set_action(srv_camera_id, service_name):
    '''
    Esta function transfiere la configuration de los parametros hacia los servicios activos por cada camara
    '''
    global action, scfg

    execute_actions = False
    if service_name in com.SERVICES:
        action.update({srv_camera_id: service_name})

        com.log_debug('Set "{}" variables for service id: {}'.format(service_name, srv_camera_id))
        if service_name == 'find':
            if service_name == com.SERVICE_DEFINITION[com.SERVICES[service_name]]:
                com.log_error("Servicio de find no definido aun")
            else:
                com.log_error("Servicio '"+service_name+"' no definido")
        elif service_name == 'blackList':
            if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]] and BLACKLIST_DB_NAME:
                config_blacklist(srv_camera_id)
                execute_actions = True
            else:
                com.log_error("Servicio '"+service_name+"' no definido")
        elif service_name == 'whiteList':
            if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]] and WHITELIST_DB_NAME:
                config_whitelist(srv_camera_id)
                execute_actions = True
            else:
                com.log_error("Servicio '"+service_name+"' no definido")
        elif service_name == 'ageAndGender':
            if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]]:
                config_age_and_gender(srv_camera_id)
                execute_actions = True
            else:
                com.log_error("Servicio '"+service_name+"' no definido")
        elif service_name == 'aforo':
            if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]]:
                validate_aforo_values(scfg, srv_camera_id, service_name)
                set_aforo(scfg, srv_camera_id, service_name)
                set_initial_last_disappeared(srv_camera_id[7:24])
                execute_actions = True
            else:
                com.log_error("Servicio '"+service_name+"' no definido")

        if execute_actions:
            com.log_debug("Adjusted configuration: ")
            print(scfg)
            return True

    com.log_error('Unable to set up value: {}, must be one of this: {}'.format(service_name, com.SERVICES))


def main():
    global scfg, call_order_of_keys, header

    header = set_header()
    scfg = srv.get_server_info(header)
    com.log_debug("Final configuration: \n{}".format(scfg))

    number_sources = 0
    for camera_mac in scfg:
        call_order_of_keys.append(camera_mac)
        number_sources += 1
        for service_id in scfg[camera_mac]:
            if service_id == "source" or service_id == "server_url":
                continue
            for item in scfg[camera_mac][service_id]:
                for service_id_inner in item:
                    for service_name in item[service_id_inner]:
                        set_action(service_id_inner, service_name)
    is_live = False

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    com.log_debug("Creating Pipeline")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    # Create nvstreammux instance to form batches from one or more sources.
    com.log_debug("Creating streamux")
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create NvStreamMux \n")

    # Create Pipeline element that will form a connection of other elements
    com.log_debug("Creating Pipeline")
    pipeline.add(streammux)

    # Se crea elemento que acepta todo tipo de video o RTSP
    i = 0
    for ordered_key in call_order_of_keys:
        fps_streams["stream{0}".format(i)] = GETFPS(i)
        frame_count["stream_"+str(i)] = 0
        saved_count["stream_"+str(i)] = 0

        # Defining only 1 active source per camera 
        for service_id in scfg[ordered_key]:
            uri_name = scfg[ordered_key]['source']

            com.log_debug("Creating source_bin: {}.- {} with uri_name: {}\n".format(i, ordered_key, uri_name))

            if uri_name.find("rtsp://") == 0 :
                is_live = True

            source_bin = create_source_bin(i, uri_name)
            if not source_bin:
                com.log_error("Unable to create source bin")

            pipeline.add(source_bin)
            padname = "sink_%u" % i

            sinkpad = streammux.get_request_pad(padname)
            if not sinkpad:
                com.log_error("Unable to create sink pad bin")
            srcpad = source_bin.get_static_pad("src")
            if not srcpad:
                com.log_error("Unable to create src pad bin")
            srcpad.link(sinkpad)
            i += 1
            break

    com.log_debug("Numero de fuentes :{}".format(number_sources))
    print("\n------ Fps_streams: ------ \n", fps_streams)


    '''
    -------- Configuration loaded --------
    '''

    print("Creating Decoder \n")
    decoder = Gst.ElementFactory.make("nvv4l2decoder", "nvv4l2-decoder")
    if not decoder:
        sys.stderr.write(" Unable to create Nvv4l2 Decoder \n")

    # Use nvinfer to run inferencing on decoder's output,
    # behaviour of inferencing is set through config file
    
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write(" Unable to create pgie \n")

    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    if not tracker:
        sys.stderr.write(" Unable to create tracker \n")

    #
    #  version 2.1 no realizara inferencias secundarias.
    #  por lo que sgie1, sgie2 y sgie3 no estaran habilitados
    #
    
    #sgie1 = Gst.ElementFactory.make("nvinfer", "secondary1-nvinference-engine")
    #if not sgie1:
    #    sys.stderr.write(" Unable to make sgie1 \n")

    #sgie2 = Gst.ElementFactory.make("nvinfer", "secondary2-nvinference-engine")
    #if not sgie1:
    #    sys.stderr.write(" Unable to make sgie2 \n")

    #sgie3 = Gst.ElementFactory.make("nvinfer", "secondary3-nvinference-engine")
    #if not sgie3:
    #    sys.stderr.write(" Unable to make sgie3 \n")
        
    #
    #   La misma version 2.1 debe permitir opcionalmente mandar a pantalla o no
    #
    # 11-nov-2021
    # si estamos en DEMO mode se manda a pantalla, todo a través del elemento sink
    # 
    #demo_status = com.FACE_RECOGNITION_DEMO
    #if demo_status == "True":
    #    sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
    #else:
    #    sink = Gst.ElementFactory.make("fakesink", "fakesink")

    print("Creating tiler \n ")
    tiler = Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
    if not tiler:
        sys.stderr.write(" Unable to create tiler \n")
        
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvidconv \n")

    # Create OSD to draw on the converted RGBA buffer
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")

    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")

    # Finally render the osd output
    if is_aarch64():
        transform = Gst.ElementFactory.make("nvegltransform", "nvegl-transform")

    print("Creating EGLSink \n")
    sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
    sink.set_property('sync', 0)
    if not sink:
        sys.stderr.write(" Unable to create egl sink \n")
        
    if is_live:
        print("At least one of the sources is live")
        streammux.set_property('live-source', 1)
        #streammux.set_property('live-source', 1)
        
    # Tamano del streammux, si el video viene a 720, se ajusta automaticamente

    streammux.set_property('width', MUXER_OUTPUT_WIDTH)
    streammux.set_property('height', MUXER_OUTPUT_HEIGHT)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)

    #
    # Configuracion de modelo
    # dstest2_pgie_config contiene modelo estandar, para  yoloV3, yoloV3_tiny y fasterRCNN
    #

    #pgie.set_property('config-file-path', CURRENT_DIR + "/configs/dstest2_pgie_config.txt")
    #pgie.set_property('config-file-path', CURRENT_DIR + "/configs/config_infer_primary_nano.txt") 
    #pgie.set_property('config-file-path', CURRENT_DIR + "/configs/deepstream_app_source1_video_masknet_gpu.txt")
    #pgie.set_property('config-file-path', CURRENT_DIR + "/configs/config_infer_primary_yoloV3.txt")
    pgie.set_property('config-file-path', CURRENT_DIR + "/configs/kairos_peoplenet_pgie_config.txt")
    #pgie.set_property('config-file-path', CURRENT_DIR + "/configs/config_infer_primary_yoloV3_tiny.txt")
    #pgie.set_property('config-file-path', CURRENT_DIR + "/configs/config_infer_primary_fasterRCNN.txt")
    # Falta añadir la ruta completa del archivo de configuracion
    
    pgie_batch_size = pgie.get_property("batch-size")
    print(pgie_batch_size)
    if pgie_batch_size != number_sources:
        print("WARNING: Overriding infer-config batch-size", pgie_batch_size,
              " with number of sources ", number_sources, " \n")
        pgie.set_property("batch-size", number_sources)
    
    # Set properties of pgie and sgiae
    # version 2.1 no configura inferencias secundarias
    #

    #sgie1.set_property('config-file-path', CURRENT_DIR + "/configs/dstest2_sgie1_config.txt")
    #sgie2.set_property('config-file-path', CURRENT_DIR + "/configs/dstest2_sgie2_config.txt")
    #sgie3.set_property('config-file-path', CURRENT_DIR + "/configs/dstest2_sgie3_config.txt")
    
    # Set properties of tracker
    config = configparser.ConfigParser()
    config.read('configs/dstest2_tracker_config.txt')
    #config.read('configs/kairos_peoplenet_tracker_config.txt')
    config.sections()

    for key in config['tracker']:
        if key == 'tracker-width':
            tracker_width = config.getint('tracker', key)
            tracker.set_property('tracker-width', tracker_width)
        elif key == 'tracker-height':
            tracker_height = config.getint('tracker', key)
            tracker.set_property('tracker-height', tracker_height)
        elif key == 'gpu-id':
            tracker_gpu_id = config.getint('tracker', key)
            tracker.set_property('gpu_id', tracker_gpu_id)
        elif key == 'll-lib-file':
            tracker_ll_lib_file = config.get('tracker', key)
            tracker.set_property('ll-lib-file', tracker_ll_lib_file)
        elif key == 'll-config-file':
            tracker_ll_config_file = config.get('tracker', key)
            tracker.set_property('ll-config-file', tracker_ll_config_file)
        elif key == 'enable-batch-process':
            tracker_enable_batch_process = config.getint('tracker', key)
            tracker.set_property('enable_batch_process', tracker_enable_batch_process)
            
    # Creacion del marco de tiler 
    tiler_rows = int(math.sqrt(number_sources))                           # Example 3 = 1 renglones 
    tiler_columns = int(math.ceil((1.0 * number_sources)/tiler_rows))     # Example 3 = 3 columnas 
    tiler.set_property("rows", tiler_rows)
    tiler.set_property("columns", tiler_columns)
    tiler.set_property("width", TILED_OUTPUT_WIDTH)
    tiler.set_property("height", TILED_OUTPUT_HEIGHT)
            
    print("Adding elements to Pipeline \n")
    
    #
    #  version 2.1 no requiere inferencias secundarias
    #

    pipeline.add(decoder)
    pipeline.add(pgie)
    pipeline.add(tracker)
    #pipeline.add(sgie1)
    #pipeline.add(sgie2)
    #pipeline.add(sgie3)
    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)
    if is_aarch64():
        pipeline.add(transform)

    # we link the elements together
    # source_bin -> -> nvh264-decoder -> PGIE -> Tracker
    # tiler -> nvvidconv -> nvosd -> video-renderer
    print("Linking elements in the Pipeline \n")
    
    #source.link(h264parser)
    #h264parser.link(decoder)

    # lineas ya ejecutadas en el for anterior
    #sinkpad = streammux.get_request_pad("sink_0")
    #if not sinkpad:
    #    sys.stderr.write(" Unable to get the sink pad of streammux \n")
    #srcpad = decoder.get_static_pad("src")
    #if not srcpad:
    #    sys.stderr.write(" Unable to get source pad of decoder \n")

    srcpad.link(sinkpad)    
    source_bin.link(decoder)
    decoder.link(streammux)
    streammux.link(pgie)
    pgie.link(tracker)
    tracker.link(tiler)

    #tracker.link(sgie1)
    #sgie1.link(sgie2)
    #sgie2.link(sgie3)
    #sgie3.link(tiler)

    tiler.link(nvvidconv)
    nvvidconv.link(nvosd)
    
    if is_aarch64():
        nvosd.link(transform)
        transform.link(sink)
    else:
        nvosd.link(sink)

    # create and event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.

    tiler_src_pad = tracker.get_static_pad("src")
    if not tiler_src_pad:
        sys.stderr.write(" Unable to get src pad \n")
    else:
        tiler_src_pad.add_probe(Gst.PadProbeType.BUFFER, tiler_src_pad_buffer_probe, 0)
    
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    
    # start play back and listed to events
    try:
        loop.run()
    except Exception as e:
        print("This line? "+str(e))
        pass

    # cleanup
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    sys.exit(main())
