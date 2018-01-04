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

    def _get_end_date(self):
        """Returns end date with current day of the current month"""
        current_date = datetime.today().strftime('%Y-%m-%d')
        return current_date

    def _get_pricelist_end_date(self):
        """Returns end date for price lists"""
        current_year = datetime.today().strftime('%Y')
        current_month = datetime.today().strftime('%m')
        day = datetime.today().strftime('%d')

        if int(current_month) == 12:
            year = str(int(current_year) + 1)
            month = '01'
        else:
            year = current_year
            month = str(int(current_month) + 1)
            if len(month) == 1:
                month = '0{0}'.format(month)

        pricelist_end_date = '{0}-{1}-{2}'.format(year, month, day)

        return pricelist_end_date

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=_get_date)
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=_get_end_date)
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
    pricelist_start_date = fields.Date(
        string='Start Date',
        required=True,
        default=_get_end_date)
    pricelist_end_date = fields.Date(
        string='End Date',
        required=True,
        default=_get_pricelist_end_date)

    def diff_month(self, d1, d2):
        """Returns the number of months of diff between two dates"""

        return (d1.year - d2.year) * 12 + d1.month - d2.month

    @api.multi
    def apply_discounts_to_customers(self):
        """Process all customers and gives them discounts (through price lists)
        according to their volume of purchase"""

        self.ensure_one()
        wizard_data = self.read(
            ['start_date',
             'end_date',
             'pricelist_start_date',
             'pricelist_end_date'])[0]

        date1 = datetime.strptime(wizard_data['start_date'], '%Y-%m-%d')
        date2 = datetime.strptime(wizard_data['end_date'], '%Y-%m-%d')
        number_months = abs(self.diff_month(date1, date2)) + 1

        ResPartner = self.env['res.partner']
        customers = ResPartner.search([
            ('customer', '=', True),
            ('invoice_ids', '!=', False),
            ('invoice_ids.state', 'in', ['paid', 'open']),
            ('invoice_ids.date_invoice', '>=', wizard_data['start_date']),
            ('invoice_ids.date_invoice', '<=', wizard_data['end_date']),
        ])

        PricelistCustomerDiscountPurchase = self.env[
            'pricelist.customer.discount.purchase']
        ProductPricelist = self.env['product.pricelist']
        ProductPricelistItem = self.env['product.pricelist.item']
        CustomerDiscountWizard = self.env['customer.discount.wizard']
        AccountInvoice = self.env['account.invoice']

        for customer in customers:

            customer_invoices_paid = customer.invoice_ids.filtered(
                lambda inv: inv.state == 'paid' and
                inv.type == 'out_invoice' and
                inv.date_invoice >= wizard_data['start_date'] and
                inv.date_invoice <= wizard_data['end_date']
            )

            total_refund = 0

            for inv in customer_invoices_paid:

                refund_invoices = AccountInvoice.search([
                    ('type', '=', 'out_refund'),
                    ('origin', '=', inv.number),
                    ('state', 'in', ['open', 'paid']),
                ])

                if refund_invoices:
                    total_refund += sum(refund_invoices.mapped('amount_total'))

            customer_invoices_open = customer.invoice_ids.filtered(
                lambda inv: inv.state == 'open' and
                inv.type == 'out_invoice' and
                inv.date_invoice >= wizard_data['start_date'] and
                inv.date_invoice <= wizard_data['end_date']
            )

            total_partial_payments = 0

            for inv in customer_invoices_open:

                if inv.payment_move_line_ids:

                    total_partial_payments += sum(
                        inv.payment_move_line_ids.mapped('credit'))

            for child in customer.child_ids:

                child_invoices_open = child.invoice_ids.filtered(
                    lambda inv: inv.state == 'open' and
                    inv.type == 'out_invoice' and
                    inv.date_invoice >= wizard_data['start_date'] and
                    inv.date_invoice <= wizard_data['end_date']
                )

                for inv in child_invoices_open:

                    if inv.payment_move_line_ids:

                        total_partial_payments += sum(
                            inv.payment_move_line_ids.mapped('credit'))

            customer_total_paid = sum(
                customer_invoices_paid.mapped('amount_total')) - total_refund \
                + total_partial_payments

            customer_purchase_avg = customer_total_paid / number_months
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

                discount_customer_by_category = \
                    customer.company_id.discount_customer_purchases_by_category

                if customer.property_product_pricelist:

                    customer_pricelist = \
                        customer.property_product_pricelist.copy({
                            'partner_id': customer.id,
                            'name': pricelist_name,
                        })

                    if not discount_customer_by_category:

                        item_global = False

                        for item in customer_pricelist.item_ids:

                            if item.applied_on == '3_global':

                                if not item_global:
                                    item_global = True

                            if item.compute_price == 'percentage':
                                item.percent_price += discount_for_customer

                                if item.percent_price > \
                                        customer_pricelist.last_additional_discount:

                                    item.percent_price -= \
                                        customer_pricelist.last_additional_discount

                                item.date_start = wizard_data[
                                    'pricelist_start_date']
                                item.date_end = wizard_data[
                                    'pricelist_end_date']

                            if item.compute_price == 'formula':
                                item.price_discount += discount_for_customer

                                if item.price_discount > \
                                        customer_pricelist.last_additional_discount:

                                    item.price_discount -= \
                                        customer_pricelist.last_additional_discount

                                item.date_start = wizard_data[
                                    'pricelist_start_date']
                                item.date_end = wizard_data[
                                    'pricelist_end_date']

                            if item.applied_on == '2_product_category' and \
                                    item.auto_added:

                                if item.compute_price == 'percentage':
                                    item.percent_price -= discount_for_customer

                                if item.compute_price == 'formula':
                                    item.price_discount -= discount_for_customer

                        if not item_global:
                            ProductPricelistItem.create({
                                'auto_added': True,
                                'applied_on': '3_global',
                                'compute_price': 'percentage',
                                'percent_price': discount_for_customer,
                                'pricelist_id': customer_pricelist.id,
                                'date_start': wizard_data['pricelist_start_date'],
                                'date_end': wizard_data['pricelist_end_date'],
                            })

                        customer_pricelist.last_additional_discount = \
                            discount_for_customer

                    else:

                        item_category = False

                        discount_customer_category = \
                            customer.company_id.discount_customer_purchases_category

                        for item in customer_pricelist.item_ids:

                            if item.applied_on == '3_global' and \
                                    item.auto_added:

                                customer_pricelist.item_ids -= item
                                continue

                            if customer_pricelist.last_additional_discount > 0:

                                if item.compute_price == 'percentage' and \
                                        item.percent_price >= \
                                        customer_pricelist.last_additional_discount:

                                    item.percent_price -= \
                                        customer_pricelist.last_additional_discount

                                if item.compute_price == 'formula' and \
                                        item.price_discount >= \
                                        customer_pricelist.last_additional_discount:

                                    item.price_discount -= \
                                        customer_pricelist.last_additional_discount

                            if item.applied_on == '2_product_category' and \
                                    item.categ_id and item.categ_id.id == \
                                    discount_customer_category.id:

                                if item.compute_price == 'percentage':
                                    item.percent_price += discount_for_customer

                                if item.compute_price == 'formula':
                                    item.price_discount += discount_for_customer

                                item.date_start = \
                                    wizard_data['pricelist_start_date']
                                item.date_end = wizard_data[
                                    'pricelist_end_date']

                                if not item_category:
                                    item_category = True

                        if not item_category:

                            ProductPricelistItem.create({
                                'auto_added': True,
                                'applied_on': '2_product_category',
                                'categ_id': discount_customer_category.id,
                                'compute_price': 'percentage',
                                'percent_price': discount_for_customer,
                                'pricelist_id': customer_pricelist.id,
                                'date_start': wizard_data['pricelist_start_date'],
                                'date_end': wizard_data['pricelist_end_date'],
                            })

                    customer_pricelist.last_additional_discount = discount_for_customer
                    customer.property_product_pricelist = customer_pricelist

                else:

                    if not discount_customer_by_category:

                        customer_pricelist = ProductPricelist.create({
                            'partner_id': customer.id,
                            'name': pricelist_name,
                            'last_additional_discount': discount_for_customer,
                        })

                        ProductPricelistItem.create({
                            'auto_added': True,
                            'applied_on': '3_global',
                            'compute_price': 'percentage',
                            'percent_price': discount_for_customer,
                            'pricelist_id': customer_pricelist.id,
                            'date_start': wizard_data['pricelist_start_date'],
                            'date_end': wizard_data['pricelist_end_date'],
                        })

                    else:

                        discount_customer_category = \
                            customer.company_id.discount_customer_purchases_category

                        customer_pricelist = ProductPricelist.create({
                            'partner_id': customer.id,
                            'name': pricelist_name,
                            'last_additional_discount': discount_for_customer,
                        })

                        ProductPricelistItem.create({
                            'auto_added': True,
                            'applied_on': '2_product_category',
                            'categ_id': discount_customer_category.id,
                            'compute_price': 'percentage',
                            'percent_price': discount_for_customer,
                            'pricelist_id': customer_pricelist.id,
                            'date_start': wizard_data['pricelist_start_date'],
                            'date_end': wizard_data['pricelist_end_date'],
                        })

                    customer.property_product_pricelist = customer_pricelist

                CustomerDiscountWizard.create({
                    'partner_id': customer.id,
                    'discount': discount_for_customer,
                    'wizard_id': self.id,
                    'customer_sales_avg': customer_purchase_avg,
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
    customer_sales_avg = fields.Float('Average sales')
