{
    "ac:17:c8:62:08:5b":
    {
        "source": "file:///home/edgar/shopping_mall.mkv",
        "services":
        [
            {
                "maskDetection":
                {
                    "enabled": false
                }
            },
            {
                "socialDistancing":
                {
                    "toleratedDistance": 150.0,
                    "persistence_time": 2.0,
                    "enabled": false
                }
            },
            {
                "aforo":
                {
                    "enabled": true,
                    "reference_line": {
                        "line_coordinates": [[720, 800], [1020, 500]],
                        "line_color": [123,123,220,100],
                        "outside_area": 1
                        },
                    "max_capacity": 0,
                    "area_of_interest": {
                        "padding_right": 20,
                        "padding_left": 20,
                        "padding_top": 20,
                        "padding_bottom": 20,
                        "type": "line_inside_area"
                        }
                }
            }
        ]
    },
    "34:56:fe:a3:99:de":
    {
        "source": "rtsp://192.168.128.3:9000/live",
        "services":
        [
            {
                "socialDistancing":
                {
                    "toleratedDistance": 100.0,
                    "persistenceTime": 2.0,
                    "enabled": "False"
                }
            },
            {
            "aforo":
                {
                "enabled": "False",
                "reference_line_coordinates": [[500, 720], [1100, 720]],
                "max_capacity": 20,
                "outside_area": 1,
                "area_of_interest": [90,90,0,0],
                "area_of_interest_type": "horizontal"
                }
            }
        ]
    }
}
