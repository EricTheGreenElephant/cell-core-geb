# Dataset for manual QR Code Generation
SKU_DATA_SPECS = {
    'GEB-CS10KTCS-4': {
        'product_type': '10K',
        'surface_area': '10197'
    },
    'GEB-CS6KTCS-2': {
        'product_type': '6K',
        'surface_area': '6001'
    },
    'GEB-CS6KTCS-4': {
        'product_type': '6K',
        'surface_area': '6124'
    },
    'GEB-CSmTCS': {
        'product_type': 'CS MINI',
        'surface_area': '856'
    },
    'GEB-CSmTC2S': {
        'product_type': 'CS MINI',
        'surface_area': '851'
    },
    'GEB-CSmTCS-2': {
        'product_type': 'CS MINI',
        'surface_area': '851'
    },
}

QR_LABEL_MAP = [
    {
        'labels': ['CS10K-6K_v1', 'CS10K-6K_v2', 'CS10K-6K_v3'],
        'allowed_skus': ['GEB-CS10KTCS-4', 'GEB-CS6KTCS-2', 'GEB-CS6KTCS-4'],
        'label_specs': {
            'product_sku': { 
                'position': (380, 40),
                'font_size': 44
            },
            'product_type': {
                'position': (270, 169),
                'font_size': 44
            },
            'surface_area': {
                'position': (150, 245),
                'font_size': 40
            },
            'product_id': {
                'position': (210, 545),
                'font_size': 42
            },
            'expiration_formatted': {
                'position': (210, 660),
                'font_size': 42
            }
        },
        'qr_required': True,
        'qr_specs': {
            'qr_position': (613, 333),
            'qr_size': 270,
            'qr_data': ""
        },
        'print_size': 76
    },
    {
        'labels': ['CSmini_v1', 'CSmini_v2'],
        'allowed_skus': ['GEB-CSmTCS', 'GEB-CSmTC2S', 'GEB-CSmTCS-2'],
        'label_specs': {
            'product_sku': {
                'position': (170, 248),
                'font_size': 32
            },
            'surface_area': {
                'position': (152, 166),
                'font_size': 26
            },
            'product_id': {
                'position': (170, 292),
                'font_size': 30
            },
            'expiration_formatted': {
                'position': (205, 340),
                'font_size': 30
            }
        },
        'qr_required': True,
        'qr_specs': {
            'qr_position': (457, 333),
            'qr_size': 135,
            'qr_data': ""
        },
        'print_size': 50
    },
    {
        'labels': ['CSmini_v3'],
        'allowed_skus': ['GEB-CSmTCS', 'GEB-CSmTC2S', 'GEB-CSmTCS-2'],
        'label_specs': {
            'product_sku': {
                'position': (440, 35),
                'font_size': 44
            },
            'surface_area': {
                'position': (150, 246),
                'font_size': 42
            },
            'product_id': {
                'position': (210, 550),
                'font_size': 34
            },
            'expiration_formatted': {
                'position': (210, 660),
                'font_size': 42
            }
        },
        'qr_required': True,
        'qr_specs': {
            'qr_position': (613, 275),
            'qr_size': 270,
            'qr_data': ""
        },
        'print_size': 76
    },
    {
        'labels': ['Tridock'],
        'allowed_skus': ['GEB-CSmTD'],
        'label_specs': {
            'product_sku': {
                'position': (590, 35),
                'font_size': 44
            },
        },
        'qr_required': False,
        'qr_specs': {},
        'print_size': 76
    }
]
