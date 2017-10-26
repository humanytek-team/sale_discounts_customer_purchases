# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from datetime import datetime
import operator

from openerp import api, fields, models
from openerp.tools.translate import _

OPERATORS = {
    '=': operator.eq,
    '<=': operator.le,
    '<': operator.lt,
    '>=': operator.ge,
    '>': operator.gt,
}


class PricelistCustomerDiscountPurchaseWizard(models.TransientModel):
    _name = 'pricelist.customer.discount.purchase.wizard'

    def _get_date(self):
        """Returns date with first day of the current month"""
        current_date = datetime.today().strftime('%Y-%m-')
        date_first_day_month = '{0}{1}'.format(current_date, '01')
        return date_first_day_month

    date = fields.Date(
        string='Date',
        required=True,
        default=_get_date)
    customer_discount_ids = fields.One2many(
        'customer.discount.wizard',
        'wizard_id',
        'Customer discounts'
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('processed', 'Processed'),
            ('no_discounts', 'No discounts'),
        ],
        'State',
        default='draft')

    @api.multi
    def apply_discounts_to_customers(self):
        """Process all customers and gives them discounts (through price lists)
        according to their volume of purchase"""

        self.ensure_one()
        wizard_data = self.read(['date'])[0]
        ResPartner = self.env['res.partner']
        customers = ResPartner.search([
            ('customer', '=', True),
            ('invoice_ids', '!=', False),
            ('invoice_ids.state', 'in', ['paid']),
            ('invoice_ids.date_invoice', '>=', wizard_data['date']),
        ])

        PricelistCustomerDiscountPurchase = self.env[
            'pricelist.customer.discount.purchase']
        ProductPricelist = self.env['product.pricelist']
        ProductPricelistItem = self.env['product.pricelist.item']
        CustomerDiscountWizard = self.env['customer.discount.wizard']

        for customer in customers:

            customer_invoices_paid = customer.invoice_ids.filtered(
                lambda inv: inv.state == 'paid' and
                inv.date_invoice >= wizard_data['date']
            )
            customer_total_paid = sum(
                customer_invoices_paid.mapped('amount_total'))
            customer_purchase_avg = customer_total_paid / len(
                customer_invoices_paid)
            discounts_configured = PricelistCustomerDiscountPurchase.search(
                [], order='average_sales')
            discount_for_customer = False

            for discount in discounts_configured:

                if OPERATORS[discount.op](
                        customer_purchase_avg, discount.average_sales):

                    discount_for_customer = discount.discount_rate

            if discount_for_customer:

                pricelist_name = '%s (%s)' % (
                    _('Price list'), customer.name)

                if customer.property_product_pricelist:

                    customer_pricelist = \
                        customer.property_product_pricelist.copy({
                            'partner_id': customer.id,
                            'name': pricelist_name,
                        })

                    pricelist_item_discount_added_manual = False

                    for item in customer_pricelist.item_ids:

                        if item.applied_on == '3_global' and \
                                item.compute_price == 'percentage':

                            if not item.auto_added:
                                pricelist_item_discount_added_manual = item

                            else:
                                customer_pricelist.item_ids -= item

                    customer_discount = 0.0
                    if pricelist_item_discount_added_manual:
                        customer_discount = \
                            pricelist_item_discount_added_manual.percent_price

                    ProductPricelistItem.create({
                        'auto_added': True,
                        'applied_on': '3_global',
                        'compute_price': 'percentage',
                        'percent_price': \
                            discount_for_customer + customer_discount,
                        'pricelist_id': customer_pricelist.id,
                    })

                    customer.property_product_pricelist = customer_pricelist

                else:

                    customer_pricelist = ProductPricelist.create({
                        'partner_id': customer.id,
                        'name': pricelist_name,
                    })

                    ProductPricelistItem.create({
                        'auto_added': True,
                        'applied_on': '3_global',
                        'compute_price': 'percentage',
                        'percent_price': discount_for_customer,
                        'pricelist_id': customer_pricelist.id,
                        })

                    customer.property_product_pricelist = customer_pricelist

                CustomerDiscountWizard.create({
                    'partner_id': customer.id,
                    'discount': discount_for_customer,
                    'wizard_id': self.id,
                })

        if self.customer_discount_ids:
            self.state = 'processed'
        else:
            self.state = 'no_discounts'

        view = self.env.ref(
            'sale_discounts_customer_purchases.customer_discount_wizard_form')
        return {
            'context': self._context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pricelist.customer.discount.purchase.wizard',
            'views': [(view.id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id
        }


class CustomerDiscountWizard(models.TransientModel):
    _name = 'customer.discount.wizard'

    partner_id = fields.Many2one('res.partner', 'Customer')
    discount = fields.Float('Discount')
    wizard_id = fields.Many2one(
        'pricelist.customer.discount.purchase.wizard',
        'Wizard')
