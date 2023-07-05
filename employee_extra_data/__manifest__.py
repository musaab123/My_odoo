# -*- coding: utf-8 -*-


{
    'name': 'Informations of Employee',
    'version': '16.0.1.0.0',
    'category': 'Contacts',
    'description': 'Adding new information fields in partners,sales,purchase and accounts.',
    'summary': 'Adding new information fields in partners,sales,purchase and accounts.',
    'author': 'PROSYS',
    'company': 'PROSYS',
    'maintainer': 'ZIAD HASSAN',
    'depends': ['base', 'hr'],
    'data': [

        'security/certificate_custom_group.xml',
        'views/sales_view.xml',
        'reports/report.xml',
        'reports/sale_header_custom.xml',
        'reports/delevry_slip_custom.xml',
        'reports/sallary_certficate_template.xml',
        
    ],
    'installable': True,
    'application': False,
}

