# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Manager of discounts by customer purchases',
    'version': '9.0.1.1.3',
    'category': 'Sales',
    'author': 'Humanytek',
    'website': "http://www.humanytek.com",
    'license': 'AGPL-3',
    'depends': ['product', 'sale', 'account', ],
    'data': [
        'security/ir.model.access.csv',
        'views/pricelist_customer_discount_purchase_view.xml',
        'views/res_company_view.xml',
        'wizard/pricelist_customer_discount_purchase_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': False
}
