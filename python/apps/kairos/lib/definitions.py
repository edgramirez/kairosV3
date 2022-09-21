server_url = {
        'server_url': 'str'
        }

source = {
        'source': 'str'
        }

find = {
        "find": {
            "obligatory": {
                'enabled': 'bool',
                },
            'optional': {
                'generalFaceDectDbFile':    'str',
                'checkBlackList':           'bool',
                'blacklistDbFile':          'str',
                'checkWhiteList':           'bool',
                'whitelistDbFile':          'str',
                'ignorePreviousDb':         'bool',
                'saveFacesDb':              'bool'
                }
            },
        }

blacklist = {
        "blackList": {
            'obligatory': {
                'enabled':  'bool',
                },
            'optional': {
                'dbName':   'str'
                }
            }
        }

whitelist = {
        "whiteList": {
            'obligatory': {
                'enabled':  'bool',
                },
            'optional': {
                'dbName':   'str'
                }
            }
        }

recurrence = {
        "recurrence": {
            'obligatory': {
                'enabled':  'bool',
                },
            'optional': {
                'generalFaceDectDbFile':    'str',
                'checkBlackList':           'bool',
                'blacklistDbFile':          'str',
                'checkWhiteList':           'bool',
                'whitelistDbFile':          'str'
                }
            }
        }

ageGender = {
        "ageAndGender": {
            'obligatory': {
                'enabled':  'bool'
                },
            'optional': {
                'generalFaceDectDbFile':    'str',
                'ignorePreviousDb':         'bool',
                'saveFacesDb':              'bool'
                }
            }
        }

aforo = {
        "aforo": {
            'obligatory': {
                'enabled':  'bool',
                'endpoint': 'str'
                },
            'optional': {
                'reference_line': 'list',
                'line_coordinates': 'list',
                'line_width': 'int',
                'line_color': 'list',
                'outside_area': 'int',
                'area_of_interest': 'list',
                'type': 'str',
                'max_capacity': 'int'
                }
            }
        }

socialDistancing = {
        "socialDistancing": {
            'obligatory': {
                'enabled': 'bool',
                'toleratedDistance': 'float',
                'persistenceTime': 'float'
                },
            'optional': {
                'height': 'int',
                'xyPosition': 'list',
                'angleToTheGround': 'int'
                }
            }
        }

maskDetection = {
        "maskDetection": {
            'obligatory': {
                'enabled': 'bool'
                }
            }
        }
