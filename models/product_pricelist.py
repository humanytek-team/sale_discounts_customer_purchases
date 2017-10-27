# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    partner_id = fields.Many2one('res.partner', 'Partner')
    last_additional_discount = fields.Float('Last additional discount')


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    auto_added = fields.Boolean('Auto added')
