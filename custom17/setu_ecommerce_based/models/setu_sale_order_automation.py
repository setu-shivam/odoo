# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SetuSaleOrderAutomation(models.Model):
    _name = "setu.sale.order.automation"
    _description = "Sale WorkFlow Automation"

    @api.model
    def _get_set_default_journal(self):
        company_id = self._context.get('company_id', self.env.company.id)
        return self.env['account.journal'].search([('type', '=', "sale"), ('company_id', '=', company_id)], limit=1)

    is_confirm_order = fields.Boolean(string="Confirm Order", default=False)
    is_create_invoice = fields.Boolean(string='Create Invoice', default=False)
    is_validate_invoice = fields.Boolean(string='Validate Invoice', default=False)
    is_register_payment = fields.Boolean(string='Register Payment', default=False)
    is_lock_order = fields.Boolean(string="Lock Confirmed Order", default=False)
    is_order_date_same_as_invoice_date = fields.Boolean(string='Invoice Date Same As Order')


    name = fields.Char(string="Name", translate=True)

    picking_policy = fields.Selection(
        [('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
        string='Shipping Policy', default="one")

    journal_id = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ['cash', 'bank'])])
    sale_journal_id = fields.Many2one('account.journal', string='Sales Journal', default=_get_set_default_journal,
                                      domain=[('type', '=', 'sale')])
    inbound_payment_method_id = fields.Many2one('account.payment.method', string="Debit Method",
                                                domain=[('payment_type', '=', 'inbound')])

    @api.onchange("is_confirm_order")
    def onchange_confirm_order(self):
        for record_id in self:
            if not record_id.is_confirm_order:
                record_id.is_create_invoice = False

    @api.onchange("is_create_invoice")
    def onchange_create_invoice(self):
        for record_id in self:
            if not record_id.is_create_invoice:
                record_id.is_register_payment = False

    @api.model
    def sale_order_automation(self, order_automation_id=False, order_ids=[]):
        sale_order_obj = self.env['sale.order']
        if not order_automation_id:
            sale_order_automation_ids = self.search([])
        else:
            sale_order_automation_ids = self.browse(order_automation_id)
        if not order_ids:
            sale_order_ids = sale_order_obj.search(
                [('setu_sale_order_automation_id', 'in', sale_order_automation_ids.ids),
                 ('state', 'not in', ('done', 'cancel', 'sale')), ('invoice_status', '!=', 'invoiced')])
        else:
            sale_order_ids = sale_order_obj.search(
                [('setu_sale_order_automation_id', 'in', sale_order_automation_ids.ids), ('id', 'in', order_ids)])
        sale_order_ids.create_order_process_validation()
        return True

    def automated_confirm_shipped_order(self, orders):
        self.ensure_one()
        module_obj = self.env['ir.module.module']
        stock_location_obj = self.env["stock.location"]
        mrp_module_id = module_obj.sudo().search([('name', '=', 'mrp'), ('state', '=', 'installed')])
        customer_location_id = stock_location_obj.search([("usage", "=", "customer")], limit=1)
        shipped_order_ids = orders.filtered(lambda x: x.order_line)
        for order_id in shipped_order_ids:
            order_id.state = 'sale'
            order_id.auto_shipping_order_confirm(customer_location_id, mrp_module_id)
            order_id.validate_invoice_create_payment(order_id.setu_sale_order_automation_id)
        return True
