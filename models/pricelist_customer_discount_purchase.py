# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import fields, models


class PricelistCustomerDiscountPurchase(models.Model):
    """record discounts by customer purchases"""

    _name = 'pricelist.customer.discount.purchase'
    _rec_name = 'discount_rate'

    average_sales = fields.Float('Average Sales', required=True)
    op = fields.Selection([
        ('=', '='),        
        ('>', '>'),
        ('<', '<'),
        ('>=', '>='),
        ('<=', '<=')
        ], required=True, default='>=')
    discount_rate = fields.Float('Discount rate (%)', required=True)
    pricelist_ids = fields.Many2many(
        'product.pricelist',
        string='Pricelists',
        column1='customer_discount_id',
        column2='pricelist_id',
        readonly=True)
