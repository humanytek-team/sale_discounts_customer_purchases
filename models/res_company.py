# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    discount_customer_purchases_by_category = fields.Boolean(
        'Enable discounts on customers over a category of products')
    discount_customer_purchases_category = fields.Many2one(
        'product.category',
        'Category'
    )
