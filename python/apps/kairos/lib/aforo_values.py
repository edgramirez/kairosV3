import lib.common as com


def validate_aforo_values(data):

    if 'enabled' not in data.keys():
        com.error_msg('Key element enabled does not exists in the data provided:\n\n {}'.format(data))
    else:
        if not isinstance(data['enabled'], str):
            com.error_msg("'aforo_data' parameter, most be True or False, current value: {}".format(data['enabled']))

    if 'reference_line_coordinates' in data.keys():
        reference_line_coordinates = data['reference_line_coordinates']
        reference_line_coordinates = reference_line_coordinates.replace('(', '')
        reference_line_coordinates = reference_line_coordinates.replace(')', '')
        reference_line_coordinates = reference_line_coordinates.replace(' ', '')
        reference_line_coordinates = reference_line_coordinates.split(',')
        try:
            reference_line_coordinates = [(int(reference_line_coordinates[0]), int(reference_line_coordinates[1])),
                                          (int(reference_line_coordinates[2]), int(reference_line_coordinates[3]))]
            data.update({'reference_line_coordinates': reference_line_coordinates})
        except Exception as e:
            com.error_msg("Exception: Unable to create reference_line_coordinates".format(str(e)))

        if not isinstance(data['reference_line_coordinates'], list):
            com.error_msg("reference_line_coordinate, most be a list. Undefined variable")

        if len(data['reference_line_coordinates']) != 2:
            com.error_msg("coordinates, most be a pair of values.")

        for coordinate in data['reference_line_coordinates']:
            if not isinstance(coordinate[0], int) or not isinstance(coordinate[1], int):
                com.error_msg("coordinates elements, most be integers")

        if 'reference_line_width' not in data.keys():
            data.update({'reference_line_width': 2})
        else:
            new_value = float(data['reference_line_width'])
            new_value = int(new_value)
            data.update({'reference_line_width': new_value})

        if 'reference_line_color' not in data.keys():
            data.update({'reference_line_color': [1, 1, 1, 1]})
        else:
            reference_line_color = reference_line_color.replace('(', '')
            reference_line_color = reference_line_color.replace(')', '')
            reference_line_color = reference_line_color.replace(' ', '')
            reference_line_color = reference_line_color.split(',')
            try:
                reference_line_color = [
                    int(reference_line_color[0]),
                    int(reference_line_color[1]),
                    int(reference_line_color[2]),
                    int(reference_line_color[3])
                ]
                data.update({'reference_line_color': reference_line_color})
            except Exception as e:
                com.error_msg("Exception: Unable to create reference_line_color".format(str(e)))

        if not isinstance(data['reference_line_color'], list):
            com.error_msg("coordinates color elements, most be a list of integers")

        for color in data['reference_line_color']:
            if not isinstance(color, int) or color < 0 or color > 255:
                com.error_msg("color values should be integers and within 0-255")

        if 'referenceLine' not in data.keys():
            com.error_msg("If reference line is define 'outside_area' must also be defined")
        else:
            referenceLine = float(data['referenceLine'])
            referenceLine = int(referenceLine)
            if referenceLine not in [1, 2]:
                com.error_msg("outside_area, most be an integer 1 or 2")
            data.update({'referenceLine': referenceLine})

    if 'area_of_interest' in data.keys() and data['area_of_interest'] != '':
        if 'type' not in data.keys():
            com.error_msg("Missing 'type' in 'area_of_interest' object")

        if data['type'] not in ['line_inside_area', 'parallel', 'fixed']:
            com.error_msg("'type' object value must be 'line_inside_area', 'parallel' or 'fixed'")

        up_down_left_right = data['area_of_interest'].replace(' ', '')
        up_down_left_right = up_down_left_right.split(',')
        try:
            data.update({'area_of_interest': {'up': int(up_down_left_right[0]), 'down': int(up_down_left_right[1]),
                                              'left': int(up_down_left_right[2]), 'right': int(up_down_left_right[3])}})
        except Exception as e:
            com.error_msg("Exception: Unable to get up, down, left and right values... Exception: ".format(str(e)))

        if data['type'] == 'line_inside_area':
            horizontal_keys = ['up', 'down', 'left', 'right']
            for param in horizontal_keys:
                if param not in data['area_of_interest'].keys():
                    com.error_msg("Missing '{}' parameter in 'area_of_interest' object".format(param))
        
                if not isinstance(data['area_of_interest'][param], int) or data['area_of_interest'][param] < 0:
                    com.error_msg("{} value should be integer and positive".format(param))
        elif data['type'] == 'parallel':
            print('type parallel not defined')
        elif data['type'] == 'fixed':
            inner_keys = ['topx', 'topy', 'height', 'width']
            for param in inner_keys:
                if param not in data['area_of_interest'].keys():
                    com.error_msg("Missing '{}' parameter in 'area_of_interest' object".format(param))
                if not isinstance(data['area_of_interest'][param], int) or data['area_of_interest'][param] < 0:
                    com.error_msg("{} value should be integer and positive".format(param))
        
    if 'area_of_interest' in data.keys() and 'reference_line_coordinates' in data.keys() and \
            data['type'] == 'fixed':
        com.error_msg("Incompatible parameters - reference_line is not needed when having area_of_interest type fixed")

    return data
