# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def compute_stock_move_count(self):
        for record_id in self:
            stock_move_obj = self.env['stock.move']
            record_id.stock_move_count = stock_move_obj.search_count(
                [('picking_id', '=', False), ('sale_line_id', 'in', record_id.order_line.ids)])

    stock_move_count = fields.Integer(compute="compute_stock_move_count", string="Stock Move")
    setu_sale_order_automation_id = fields.Many2one('setu.sale.order.automation', string='Sale Automation ID')
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)

    def preparation_of_sale_order_values(self, vals):
        sale_order_obj = self.env['sale.order']
        order_vals = {'company_id': vals.get('company_id', self.env.user.company_id.id),
                      'partner_id': vals.get('partner_id', False),
                      'partner_invoice_id': vals.get('partner_invoice_id', False),
                      'partner_shipping_id': vals.get('partner_shipping_id', False),
                      'warehouse_id': vals.get('warehouse_id', False)}

        new_record = sale_order_obj.new(order_vals)
        new_record._onchange_partner_id_warning()
        order_vals = sale_order_obj._convert_to_write({name: new_record[name] for name in new_record._cache})

        new_record = sale_order_obj.new(order_vals)
        new_record._onchange_partner_shipping_id()
        order_vals = sale_order_obj._convert_to_write({name: new_record[name] for name in new_record._cache})

        fiscal_position_id = order_vals.get('fiscal_position_id') or vals.get('fiscal_position_id', False)
        if vals.get('name', False):
            order_vals.update({'name': vals.get('name', '')})
        order_vals.update({'state': 'draft',
                           'picking_policy': vals.get('picking_policy'),
                           'partner_invoice_id': vals.get('partner_invoice_id', False),
                           'partner_id': vals.get('partner_id', False),
                           'partner_shipping_id': vals.get('partner_shipping_id', False),
                           'date_order': vals.get('date_order', False),
                           'pricelist_id': vals.get('pricelist_id', False),
                           'fiscal_position_id': fiscal_position_id,
                           'payment_term_id': vals.get('payment_term_id', False),
                           'team_id': vals.get('team_id', False),
                           'client_order_ref': vals.get('client_order_ref', ''),
                           'carrier_id': vals.get('carrier_id', False)})
        return order_vals

    def create_order_process_validation(self):
        for order_id in self:
            sale_order_automation_id = order_id.setu_sale_order_automation_id
            if order_id.invoice_status and order_id.invoice_status == 'invoiced':
                continue
            if sale_order_automation_id.is_confirm_order:
                order_id.process_auto_validate_sale_order_confirmation()

            order_lines = order_id.mapped('order_line').filtered(lambda l: l.product_id.invoice_policy == 'order')
            if not order_lines.filtered(lambda l: l.product_id.type == 'consu') and len(order_id.order_line) != len(
                    order_lines.filtered(lambda l: l.product_id.type in ['service', 'combo'])):
                continue
            if not order_id._check_fiscal_year_end_date():
                continue
            order_id.validate_invoice_create_payment(sale_order_automation_id)
        return True

    def _check_fiscal_year_end_date(self):
        journal = self.env['account.journal'].browse(1)
        lock_date = self.company_id._get_user_fiscal_lock_date(journal)
        if self.date_order.date() <= lock_date:
            return False
        return True

    def process_auto_validate_sale_order_confirmation(self):
        product_product_obj = self.env['product.product']
        self.ensure_one()
        product_product_obj.invalidate_recordset(fnames=['display_name'])
        self.action_confirm()
        self.write({'date_order': self.date_order})
        if self.setu_sale_order_automation_id.is_lock_order and self.state != 'done':
            self.action_lock()
        return True

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.setu_sale_order_automation_id:
            if self.setu_sale_order_automation_id.sale_journal_id:
                invoice_vals.update({'journal_id': self.setu_sale_order_automation_id.sale_journal_id.id})
            if self.setu_sale_order_automation_id.is_order_date_same_as_invoice_date:
                invoice_vals['date'] = self.date_order.date()
                invoice_vals['invoice_date'] = self.date_order.date()
        if self.multi_ecommerce_connector_id:
            invoice_vals.update({'multi_ecommerce_connector_id': self.multi_ecommerce_connector_id.id})
        return invoice_vals

    def validate_invoice_create_payment(self, sale_order_automation_id):
        self.ensure_one()
        try:
            if sale_order_automation_id.is_create_invoice:
                self._create_invoices()
            if sale_order_automation_id.is_validate_invoice:
                for invoice_id in self.invoice_ids:
                    if invoice_id.state == 'draft':
                        invoice_id.action_post()
                    if sale_order_automation_id.is_register_payment:
                        self.register_invoice_payment(sale_order_automation_id, invoice_id)
        except Exception as e:
            raise
        return True

    def register_invoice_payment(self, work_flow_process_record, move_id):
        account_payment_obj = self.env['account.payment']
        if move_id.amount_residual:
            values = self.prepare_payment_vals(work_flow_process_record, move_id)
            payment_id = account_payment_obj.create(values)
            payment_id.action_post()
            self.in_payment_validate(payment_id, move_id)
        return True

    def in_payment_validate(self, payment_id, move_id):
        move_line_obj = self.env['account.move.line']
        line_ids = move_line_obj.search([('move_id', '=', move_id.id)])
        to_reconcile = [line_ids.filtered(lambda line: line.account_type == 'asset_receivable')]

        for payment, lines in zip([payment_id], to_reconcile):
            payment_lines = payment.line_ids.filtered_domain(
                [('account_type', 'in', ('asset_receivable', 'liability_payable')), ('reconciled', '=', False)])
            for account in payment_lines.account_id:
                (payment_lines + lines).filtered_domain([('account_id', '=', account.id),
                                                         ('reconciled', '=', False)]).reconcile()
        return True

    def prepare_payment_vals(self, sale_order_automation_id, invoice_id):
        vals = {'journal_id': sale_order_automation_id.journal_id.id,
                'ref': invoice_id.payment_reference,
                'currency_id': invoice_id.currency_id.id,
                'payment_type': 'inbound',
                'date': invoice_id.date,
                'partner_id': invoice_id.commercial_partner_id.id,
                'amount': invoice_id.amount_residual,
                'payment_method_id': sale_order_automation_id.inbound_payment_method_id.id,
                'partner_type': 'customer'}
        return vals

    def auto_shipping_order_confirm(self, customer_location_id, is_mrp_module_installed=False):
        stock_location_obj = self.env['stock.location']
        order_line_ids = self.order_line.filtered(lambda l: l.product_id.type != 'service')
        supplier_location_id = stock_location_obj.search(
            ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False), ('usage', '=', 'supplier')],
            limit=1)

        for order_line_id in order_line_ids:
            bom_lines = []
            if is_mrp_module_installed:
                bom_lines = self.check_for_bom_product(order_line_id.product_id)
            for bom_line in bom_lines:
                self.auto_create_and_validate_stock_move(order_line_id, customer_location_id, bom_line=bom_line)
            if not bom_lines and order_line_id.product_id.is_drop_ship_product:
                self.auto_create_and_validate_stock_move(order_line_id, customer_location_id,
                                                         supplier_location_id=supplier_location_id)
            elif not bom_lines or not is_mrp_module_installed:
                self.auto_create_and_validate_stock_move(order_line_id, customer_location_id)
        return True

    def check_for_bom_product(self, product_id):
        try:
            bom = self.env['mrp.bom'].sudo()._bom_find(product_id, company_id=self.company_id.id, bom_type='phantom')[
                product_id]
            if bom:
                factor = product_id.uom_id._compute_quantity(1, bom.product_uom_id) / bom.product_qty
                boms, lines = bom.sudo().explode(product_id, factor, picking_type=bom.picking_type_id)
                return lines
        except Exception as e:
            _logger.info(
                "Error when trying to find BOM product components for Order {}. ERROR: {}".format(self.name, e))
        return {}

    def auto_create_and_validate_stock_move(self, order_line, customer_location_id, bom_line=False,
                                            supplier_location_id=False):
        if bom_line:
            product_id = bom_line[0].product_id
            product_qty = bom_line[1].get('qty', 0) * order_line.product_uom_qty
            product_uom_id = bom_line[0].product_uom_id
        else:
            product_id = order_line.product_id
            product_qty = order_line.product_uom_qty
            product_uom_id = order_line.product_uom

        if product_id and product_qty and product_uom_id:
            vals = {'name': _('Auto Processed Stock Move : %s') % product_id.display_name,
                    'company_id': self.company_id.id,
                    'product_id': product_id.id if product_id else False,
                    'product_uom_qty': product_qty,
                    'product_uom': product_uom_id.id if product_uom_id else False,
                    'location_id': supplier_location_id.id if supplier_location_id else self.warehouse_id.lot_stock_id.id,
                    'location_dest_id': customer_location_id and customer_location_id.id,
                    'state': 'confirmed',
                    'sale_line_id': order_line.id}
            if bom_line:
                vals.update({'bom_line_id': bom_line[0].id})
            stock_move_id = self.env['stock.move'].create(vals)
            stock_move_id._action_assign()
            stock_move_id._set_quantity_done(product_qty)
            stock_move_id._action_done()
        return True

    def action_view_stock_move(self):
        stock_move_obj = self.env['stock.move']
        move_ids = stock_move_obj.search([('picking_id', '=', False), ('sale_line_id', 'in', self.order_line.ids)]).ids
        action = {'domain': "[('id', 'in', " + str(move_ids) + " )]",
                  'name': 'Order Stock Move',
                  'view_mode': 'list,form',
                  'res_model': 'stock.move',
                  'type': 'ir.actions.act_window'}
        return action

    def check_product_dropship(self, product_id):
        location_dest_ids = self.env['stock.location'].search(
            ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False), ('usage', '=', 'customer')])
        route_ids = product_id.route_ids or product_id.categ_id.route_ids
        stock_rule = self.env['stock.rule'].search([('company_id', '=', self.env.company.id), ('action', '=', 'buy'),
                                                    ('location_dest_id', 'in', location_dest_ids.ids),
                                                    ('route_id', 'in', route_ids.ids)])
        if stock_rule:
            return True
        return False
