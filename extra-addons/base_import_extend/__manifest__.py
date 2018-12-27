# @author: Xiao
# @email: voewjwz@sina.com
# @time: 12/20/18

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': '',
    'version': '1.0.0',
    'author': 'Xiao',
    'description': """
    """,
    'category': 'ichub',
    'website': 'https://www.ichub.com',
    'depends': ['base', 'mail'],
    'data': [
        'data/data.xml',
        'views/base_import.xml',
        'views/template.xml',
    ],
    'qweb': [
        "static/src/xml/import_function.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}