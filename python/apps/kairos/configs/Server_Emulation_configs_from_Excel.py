{
    "ac:17:c8:62:08:5b":
    {
        "server_url": "http://3.219.81.19:8888/",
        "source": "file:///home/edgar/Downloads/CAM_26_Entrance_1.mp4",
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
                    "endpoint": "posts/aforo",
                    "reference_line": {
                        "line_coordinates": [[620, 400], [1220, 400]],
                        "line_color": [123,123,220,100],
                        "outside_area": 1,
                        "area_of_interest": {
                            "padding_right": 30,
                            "padding_left": 30,
                            "padding_top": 30,
                            "padding_bottom": 30
                            }
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
