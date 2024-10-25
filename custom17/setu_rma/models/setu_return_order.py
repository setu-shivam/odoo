from odoo import api, fields, models, _
from odoo.tools.translate import _
from odoo.exceptions import UserError

from odoo.exceptions import AccessError
from odoo.tools import html2plaintext
from markupsafe import Markup


class SetuReturnOrder(models.Model):
    _name = "setu.return.order"
    _description = 'Return Order Management'
    _order = "priority,date desc"
    _inherit = ['mail.thread']
    _rec_name = 'code'

    @api.constrains('stock_picking_id')
    def check_picking_id(self):
        for record in self:
            if not record.sale_order_id:
                raise UserError(_("Sale Order not found in delivery, Please select valid delivery with sale order"))

    @api.model
    def default_get(self, default_fields):
        res = super(SetuReturnOrder, self).default_get(default_fields)
        active_model = self._context.get('active_model', False)
        active_id = self._context.get('active_id', False)
        if active_model == 'sale.order' and active_id:
            if active_id := self.env[active_model].browse(active_id):
                if sale_id := active_id.picking_ids and active_id.picking_ids.filtered(
                        lambda x: x.picking_type_id.code == 'outgoing') and \
                              active_id.picking_ids.filtered(lambda x: x.picking_type_id.code == 'outgoing')[
                                  -1].id or False:
                    if picking := self.env['stock.picking'].search([('id', '=', sale_id)]):
                        res['stock_picking_id'] = picking.id
        return res

    @api.depends('stock_picking_id')
    def get_product_ids(self):
        product_ids = []
        for record in self:
            if not record.stock_picking_id:
                continue
            for move in record.stock_picking_id.move_ids:
                product_ids.append(move.product_id.id)
            record.move_product_ids = [(6, 0, move.product_id.id)]

    @api.depends('return_order_line_ids.product_id')
    def get_line_product_ids(self):
        lines = list(self.return_order_line_ids)
        for record in self:
            record.move_product_ids = [(6, 0, [p.product_id.id for p in lines])]

    @api.onchange('stock_picking_id')
    def onchange_picking_id(self):
        stock_picking = self.stock_picking_id
        stock_picking_partner = stock_picking and stock_picking.partner_id
        if not stock_picking:
            self.return_order_line_ids = False
            self.sale_order_id = False
            self.delivery_address_id = False
            self.partner_id = False
            self.partner_phone = ''
            self.email_from = ''
        if stock_picking:
            self.return_order_line_ids = False
            sale_order = stock_picking.sale_id or False
            claim_lines = [
                (0, 0, {'product_id': move.product_id.id, 'quantity': move.quantity, 'stock_move_id': move.id})
                for
                move in stock_picking.move_ids if move.quantity > 0]
            self.return_order_line_ids = claim_lines
            self.sale_order_id = sale_order
            if stock_picking_partner:
                self.delivery_address_id = stock_picking_partner.id
            rma_partner = self.sale_order_id and self.sale_order_id.partner_id or False
            if rma_partner:
                self.partner_id = rma_partner.id
                self.partner_phone = rma_partner.phone
                self.email_from = rma_partner.email
            if not stock_picking_partner and rma_partner:
                self.delivery_address_id = rma_partner.id

    @api.onchange('sale_order_id')
    def onchange_sale_id(self):
        if self.sale_order_id:
            self.section_id = self.sale_order_id and self.sale_order_id.team_id or False

    # direct add end

    def get_is_visible(self):
        for record in self:
            record.approve_button_visible = bool(
                (record.return_picking_id and record.return_picking_id.state == 'done') or (
                    record.is_approval_without_receipt))

    def get_so(self):
        for record in self:
            if record.stock_picking_id:
                record.sale_order_id = record.stock_picking_id.sale_id.id
            else:
                record.sale_order_id = False

    @api.depends('stock_picking_id')
    def get_products(self):
        for record in self:
            move_products = [move.product_id.id for move in record.stock_picking_id.move_ids]
            record.move_product_ids = [(6, 0, move_products)]

    def get_delivered_date(self):
        for record in self:
            done_date = self.env['stock.picking'].search(
                [('sale_id', '=', self.sale_order_id.id), ('picking_type_code', '=', 'outgoing'),
                 ('state', '=', 'done')], order='date_done desc', limit=1).date_done
            self.delivered_date = done_date

    def compute_is_order_invoice(self):
        for rec in self:
            if rec.sale_order_id.invoice_ids:
                rec.is_order_invoice = True
            else:
                rec.is_order_invoice = False

    active = fields.Boolean(string='Active', default=1)
    approve_button_visible = fields.Boolean(string='Is Visible', compute=get_is_visible)
    is_return_order_email_send = fields.Boolean(string="Return Order Send", copy=False)
    is_return_internal_transfer = fields.Boolean(string="Is Return Internal Transfer", default=False)
    is_approval_without_receipt = fields.Boolean(string="Is Approval Without Receipt", default=False)

    name = fields.Char(string='Description')
    user_fault = fields.Char(string='Trouble Responsible')
    email_from = fields.Char(string='Email', size=128, help="Destination email for email gateway.")
    partner_phone = fields.Char(string='Phone')

    description = fields.Text(string='Description')

    date_closed = fields.Datetime(string='Closed', readonly=True, copy=False)
    date = fields.Datetime(string='Return Date', index=True, default=fields.Datetime.now, copy=False)
    delivered_date = fields.Datetime(string='Delivered Date', readonly=True, copy=False, compute=get_delivered_date)

    state = fields.Selection([('draft', 'Draft'), ('to_be_approved', 'To Be Approved'), ('approve', 'In Progress'),
                              ('in_progress', 'In Progress'), ('done', 'Done'), ('reject', 'Rejected'),
                              ('cancel', 'Cancel')], default='draft', copy=False, tracking=True)

    user_id = fields.Many2one('res.users', string='Assigned to', tracking=True,
                              default=lambda self: self._uid)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Customer')
    account_move_id = fields.Many2one("account.move", string="Invoice", copy=False)
    sale_order_id = fields.Many2one('sale.order', string="Sale Order", compute=get_so)
    reject_message_id = fields.Many2one("setu.return.order.reject", string="Reject Reason", copy=False)
    new_sale_order_id = fields.Many2one('sale.order', string='New Sale Order', copy=False)
    location_id = fields.Many2one('stock.location', string='Return Location', domain=[('usage', '=', 'internal')])
    internal_stock_picking_id = fields.Many2one('stock.picking', string='Internal Delivery Order', default=False,
                                                copy=False)
    stock_picking_id = fields.Many2one('stock.picking', string='Delivery Order',
                                       domain="[('state','=','done'),('picking_type_id.code','=','outgoing'),('sale_id','!=',False)]")
    return_picking_id = fields.Many2one('stock.picking', string='Return Delivery Order', default=False, copy=False)
    rma_support_person_id = fields.Many2one("res.partner", string="Contact Person")

    return_order_line_ids = fields.One2many("setu.return.order.line", "return_order_id", string="Return Order Lines")
    repair_order_ids = fields.One2many('repair.order', 'return_order_id', string="Repair Order")

    move_product_ids = fields.Many2many('product.product', string="Products", compute=get_products)
    return_picking_ids = fields.Many2many('stock.picking', string='Return Delivery Orders', default=False, copy=False)
    refund_invoice_ids = fields.Many2many('account.move', string='Refund Invoices', copy=False)

    replace_invoice_ids = fields.Many2many('account.move', 'replace_invoices_ids', '', '', string='Refund Invoices',
                                           copy=False)
    is_order_invoice = fields.Boolean(string='Order Invoice', compute='compute_is_order_invoice')

    code = fields.Char(string='Return Order Number', default="New", readonly=True, copy=False)
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], 'Priority', default="1")
    section_id = fields.Many2one('crm.team', 'Sales Team', index=True,
                                 help="Responsible sales channel." \
                                      " Define Responsible user and Email account for" \
                                      " mail gateway.")
    delivery_address_id = fields.Many2one('res.partner', string='Delivery Address')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            context = dict(self._context or {})
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('setu.return.order')
            if vals.get('section_id') and not context.get('default_section_id'):
                context['default_section_id'] = vals.get('section_id')
            res = super(SetuReturnOrder, self).create(vals)
            reg = {
                'res_id': res.id,
                'res_model': 'setu.return.order',
                'partner_id': res.partner_id.id,
            }
            if not self.env['mail.followers'].search(
                    [('res_id', '=', res.id), ('res_model', '=', 'setu.return.order'),
                     ('partner_id', '=', res.partner_id.id)]):
                follower_id = self.env['mail.followers'].sudo().create(reg)
        return res

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Return order cannot be deleted once it processed.")
        return super(SetuReturnOrder, self).unlink()

    def action_return_order_send(self):
        self.ensure_one()
        self.is_return_order_email_send = True
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('setu_rma', 'mail_setu_rma_details_notification')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'setu.return.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def create_return_picking(self, claim_lines=False):
        location_id = self.location_id.id
        vals = {'picking_id': self.return_picking_id.id if claim_lines else self.stock_picking_id.id,
                'location_id': self.return_picking_id.location_id.id or self.stock_picking_id.picking_type_id.warehouse_id.lot_stock_id.id}
        if location_id and not claim_lines:
            vals['location_id'] = location_id
        return_picking_wizard = self.env['stock.return.picking'].with_context(
            active_id=self.return_picking_id.id if claim_lines else self.stock_picking_id.sale_id.id).sudo().create(vals)
        return_lines = []
        lines = claim_lines or self.return_order_line_ids
        for line in lines:
            stock_move_id = self.env['stock.move'].search([('product_id', '=', line.product_id.id),
                                                           ('picking_id', '=',
                                                            self.return_picking_id.id if claim_lines else self.stock_picking_id.id),
                                                           ('sale_line_id', '=', line.stock_move_id.sale_line_id.id), ])
            return_line = self.env['stock.return.picking.line'].create(
                {'product_id': line.product_id.id, 'quantity': line.quantity, 'wizard_id': return_picking_wizard.id,
                 'move_id': stock_move_id.id})
            return_lines.append(return_line.id)
        return_picking_wizard.write({'product_return_moves': [(6, 0, return_lines)]})
        new_picking_id, pick_type_id = return_picking_wizard._create_returns()
        pick_type_id = pick_type_id and self.env['stock.picking.type'].sudo().browse(pick_type_id) or False
        new_picking = new_picking_id and self.env['stock.picking'].sudo().browse(new_picking_id) or False
        if new_picking and pick_type_id.code == "outgoing":
            new_picking.write({
                'partner_id': self.delivery_address_id.id if self.delivery_address_id and self.delivery_address_id != self.partner_id else self.partner_id.id})
        if claim_lines:
            repair_obj = self.env['setu.return.order.reason'].sudo().search([('action', '=', 'repair')], limit=1)
            if repair_obj and new_picking:
                new_picking.write({'return_operation_id': repair_obj.id})
            self.write({'return_picking_ids': [(4, new_picking_id)]})
        else:
            self.return_picking_id = new_picking_id
        return True

    def action_return_request_approval(self):
        self.write({'state': 'to_be_approved'})
        for line in self.return_order_line_ids:
            if line.quantity <= 0 or not line.return_order_reason_id:
                raise UserError(_("Please set Return Quantity and Reason for all products."))
        if not self.is_approval_without_receipt:
            self.create_return_picking()
        return True

    def action_return_request_approval_without_receipt(self):
        self.write({'state': 'to_be_approved'})
        self.is_approval_without_receipt = True
        for line in self.return_order_line_ids:
            if not line.return_order_reason_id:
                raise UserError(_("Please set Return Reason for all products."))
        return True

    def action_return_approve(self):
        processed_product_list = []
        if len(self.return_order_line_ids) <= 0:
            raise UserError(_("Please set return products."))
        total_qty = 0
        for line in self.return_order_line_ids:
            moves = line.search([('stock_move_id', '=', line.stock_move_id.id)])
            for m in moves:
                if m.return_order_id.state in ['approve', 'done']:
                    total_qty += m.quantity
            if total_qty >= line.stock_move_id.quantity:
                processed_product_list.append(line.product_id.name)
        if processed_product_list:
            raise UserError(_('%s Product\'s delivered quantites were already processed for RMA' % (
                ", ".join(processed_product_list))))
        for line in self.return_order_line_ids:
            if not self.is_approval_without_receipt and line.return_order_id.return_picking_id and line.return_order_id.return_picking_id.state not in [
                'done', 'cancel']:
                raise UserError(_("Please first process Return Picking Order."))
        self.write({'state': 'approve'})
        self.action_return_order_send_email()
        return True

    def action_return_order_send_email(self):
        email_template = self.env.ref('setu_rma.mail_setu_rma_details_notification', False)
        mail_mail = email_template and email_template.send_mail(self.id) or False
        mail_mail and self.env['mail.mail'].browse(mail_mail).send()

    def action_return_reject(self):
        return {
            'name': "Reject Return Order",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'claim.process.wizard',
            'view_id': self.env.ref('setu_rma.setu_view_claim_reject').id,
            'type': 'ir.actions.act_window',
            'context': {'claim_lines': self.return_order_line_ids.ids},
            'target': 'new'
        }

    def action_set_to_draft(self):
        if self.return_picking_id and self.return_picking_id.state != 'draft':
            self.return_picking_id.state = 'cancel'
        self.write({'state': 'draft'})

    def action_return_receipt(self):
        if len(self.return_picking_id) == 1:
            return {
                'name': "Receipt",
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': self.return_picking_id.id
            }
        else:
            return {
                'name': "Receipt",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'domain': [('id', '=', self.return_picking_id.id)]
            }

    def action_return_repair(self):
        if len(self.repair_order_ids) == 1:
            return {
                'name': "Repair",
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'repair.order',
                'type': 'ir.actions.act_window',
                'res_id': self.repair_order_ids[0].id
            }
        else:
            return {
                'name': "Repairs",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'repair.order',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.repair_order_ids.ids)]
            }

    def action_return_delivery(self):
        if len(self.return_picking_ids.ids) == 1:
            return {
                'name': "Delivery",
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': self.return_picking_ids.id
            }
        else:
            return {
                'name': "Deliveries",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', self.return_picking_ids.ids)]
            }

    def action_return_refund(self):
        if len(self.refund_invoice_ids) != 1:
            return {
                'name': "Customer Invoices",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'views': [(self.env.ref('account.view_invoice_tree').id, 'tree'),
                          (self.env.ref('account.view_move_form').id, 'form')],
                'domain': [('id', 'in', self.refund_invoice_ids.ids), ('type', '=', 'out_refund')]
            }
        view_id = self.env.ref('account.view_move_form').id
        return {
            'name': "Customer Invoices",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_id': view_id,
            'res_id': self.refund_invoice_ids.id
        }

    def action_return_sale_order(self):
        return {
            'name': "Sale Order",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'res_id': self.new_sale_order_id.id
        }

    def action_process_return(self):
        if self.state != 'approve':
            raise UserError(_("Return Order can't process."))
        if not self.is_approval_without_receipt and self.return_picking_id.state != 'done':
            raise UserError(_("Please first validate Return Picking Order."))
        return_lines = []
        refund_lines = []
        repair_lines = []
        do_lines = []
        so_lines = []
        am_lines = []
        for line in self.return_order_line_ids:
            if not line.return_order_type:
                raise UserError(_("Please set appropriate Action for all rma lines."))
            if line.return_order_type == 'buyback':
                if not line.buyback_cost or line.buyback_cost <= 0:
                    raise UserError(
                        _(f" Return order line with product {line.product_id.name} has Buyback cost not set."))

            elif line.return_order_type == 'replace':
                if not line.to_be_replace_product_id or line.to_be_replace_quantity <= 0:
                    raise UserError(
                        _(f" Return order line with product {line.product_id.name} has Replace product or Replace quantity or both not set."))

            if line.return_order_type == 'repair':
                return_lines.append(line)
                self.create_repair_order(line)
            if line.return_order_type == 'buyback':
                so_lines.append(line)
                refund_lines.append(line)
            elif line.return_order_type == 'refund':
                refund_lines.append(line)
            elif line.return_order_type == 'replace':
                if line.is_create_invoice or line.is_create_credit_note:
                    if line.is_create_invoice:
                        so_lines.append(line)
                    if line.is_create_credit_note:
                        am_lines.append(line)
                else:
                    do_lines.append(line)
        if not self.is_approval_without_receipt:
            return_lines and self.create_return_picking(return_lines)
        refund_lines and self.create_refund(refund_lines)
        do_lines and self.create_do(do_lines)
        so_lines and self.create_so(so_lines)
        am_lines and self.create_credit_note(am_lines)

        self.state = 'done'
        self.action_return_order_send_email()
        return self

    def create_credit_note(self, lines):
        if not self.sale_order_id.invoice_ids:
            message = _("The invoice was not created for Order : "
                        "<a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>") % (
                          self.sale_order_id.id, self.sale_order_id.name)
            self.message_post(body=message)
            # ----------------------------------
            self.create_credit_note_without_invoice(lines)
            return True
            # ----------------------------------
        replace_invoice_ids_rec = []
        replace_invoice_ids = self.check_and_create_refund_invoice(lines)
        if not replace_invoice_ids:
            return False
        replace_invoice_ids_rec = self.prepare_and_create_refund_invoice(replace_invoice_ids, replace_invoice_ids_rec)
        if replace_invoice_ids_rec:
            self.write({'replace_invoice_ids': [(6, 0, replace_invoice_ids_rec)]})
        return True

    def create_credit_note_without_invoice(self, lines):
        account_move = self.env['account.move']
        customer_ref = f'Reversal of: {self.sale_order_id.name}'
        if self.name:
            customer_ref += f', Refund Process of Return - {self.name}'
        move_vals = {
            'partner_id': self.partner_id.id,
            'return_order_id': self.id,
            'ref': customer_ref,
            'invoice_origin': self.sale_order_id.name,
            'l10n_in_state_id': self.partner_id.state_id.id,
            'move_type': 'out_refund',
            'state': 'draft'
        }
        new_record = account_move.new(move_vals)
        move_vals = account_move._convert_to_write({name: new_record[name] for name in new_record._cache})
        new_record = account_move.new(move_vals)
        move_vals = account_move._convert_to_write({name: new_record[name] for name in new_record._cache})
        am = account_move.create(move_vals)
        for line in lines:
            account_move_line = self.env['account.move.line']
            if line.is_create_credit_note:
                move_line = {
                    'move_id': am.id,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'quantity': line.return_qty,
                    'price_unit': line.product_id.list_price,
                    'tax_ids': line.product_id.taxes_id,
                }
                new_move_line = account_move_line.new(move_line)
                move_line = account_move_line._convert_to_write(
                    {name: new_move_line[name] for name in new_move_line._cache})
                account_move_line.create(move_line)
            else:
                continue
        return True

    def create_repair_order(self, vals):
        repair_order = self.env['repair.order']
        repair_order_vals = {
            'product_id': vals.product_id.id,
            'product_qty': vals.return_qty,
            'location_id': self.stock_picking_id.location_id.id,
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'product_uom': vals.product_id.uom_id.id,
            'return_order_id': self.id,
            'picking_type_id':self.env['stock.picking.type'].search([('code','=','repair_operation')]).id
        }
        if vals.return_order_type == "repair":
            new_record = repair_order.new(repair_order_vals)
            # new_record.onchange_partner_id()
            repair_order_vals = repair_order._convert_to_write({name: new_record[name] for name in new_record._cache})
            new_record = repair_order.new(repair_order_vals)
            repair_order_vals = repair_order._convert_to_write({name: new_record[name] for name in new_record._cache})

            ro = repair_order.create(repair_order_vals)
            self.write({'repair_order_ids': [(4, 0, ro.id)]})
        return True

    def create_so(self, lines):
        sale_order = self.env['sale.order']
        order_vals = {
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.delivery_address_id.id if self.delivery_address_id and self.delivery_address_id != self.partner_id else self.partner_id.id,
            'warehouse_id': self.sale_order_id.warehouse_id.id,
            'return_order_id': self.id,
        }
        new_record = sale_order.new(order_vals)
        new_record._onchange_partner_id_warning()
        order_vals = sale_order._convert_to_write({name: new_record[name] for name in new_record._cache})
        new_record = sale_order.new(order_vals)
        new_record._compute_partner_shipping_id()
        order_vals = sale_order._convert_to_write({name: new_record[name] for name in new_record._cache})
        order_vals.update({
            'state': 'draft',
            'team_id': self.section_id.id,
            'client_order_ref': self.name,
        })
        so = sale_order.create(order_vals)
        self.new_sale_order_id = so.id
        for line in lines:
            sale_order_line = self.env['sale.order.line']
            order_line = {
                'order_id': so.id,
                'product_id': line.to_be_replace_product_id.id,
                'company_id': self.company_id.id,
                'name': line.to_be_replace_product_id.name
            }
            new_order_line = sale_order_line.new(order_line)
            new_order_line._onchange_product_id_warning()
            order_line = sale_order_line._convert_to_write(
                {name: new_order_line[name] for name in new_order_line._cache})
            order_line.update({
                'product_uom_qty': line.to_be_replace_quantity,
                'state': 'draft',
            })
            sale_order_line.create(order_line)
        self.write({'new_sale_order_id': so.id})
        return True

    def create_do(self, lines):
        replace_obj = self.env['setu.return.order.reason'].sudo().search([('action', '=', 'replace')], limit=1)
        do = self.env['stock.picking'].create({
            'partner_id': self.delivery_address_id.id if self.delivery_address_id and self.delivery_address_id != self.partner_id else self.partner_id.id,
            'location_id': self.stock_picking_id.location_id.id,
            'location_dest_id': self.stock_picking_id.location_dest_id.id,
            'picking_type_id': self.stock_picking_id.picking_type_id.id,
            'origin': self.name,
            'return_order_id': self.id,
            'return_operation_id': replace_obj.id if replace_obj else False
        })
        for line in lines:
            self.env['stock.move'].create({
                'location_id': self.stock_picking_id.location_id.id,
                'location_dest_id': self.stock_picking_id.location_dest_id.id,
                'product_uom_qty': line.to_be_replace_quantity or line.quantity,
                'name': line.to_be_replace_product_id.name,
                'product_id': line.to_be_replace_product_id.id,
                'state': 'draft',
                'picking_id': do.id,
                'product_uom': line.to_be_replace_product_id.uom_id.id,
                'company_id': self.company_id.id,
                # 'group_id': self.stock_picking_id.group_id.id
            })
        self.write({'return_picking_ids': [(4, do.id)]})
        do.action_assign()
        return True

    def create_refund(self, lines):
        if not self.sale_order_id.invoice_ids:
            message = _("The invoice was not created for Order : "
                        "<a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>") % (
                          self.sale_order_id.id, self.sale_order_id.name)
            self.message_post(body=Markup(message))
            return False
        refund_invoice_ids_rec = []

        refund_invoice_ids = self.check_and_create_refund_invoice(lines)
        if not refund_invoice_ids:
            return False
        refund_invoice_ids_rec = self.prepare_and_create_refund_invoice(refund_invoice_ids, refund_invoice_ids_rec)
        if refund_invoice_ids_rec:
            self.write({'refund_invoice_ids': [(6, 0, refund_invoice_ids_rec)]})
        return True

    def prepare_and_create_refund_invoice(self, refund_invoice_ids, refund_invoice_ids_rec):
        for invoice_id, lines in refund_invoice_ids.items():
            refund_invoice = self.create_reverse_move_for_invoice(invoice_id)
            if not refund_invoice:
                continue

            if refund_invoice.invoice_line_ids:
                refund_invoice.invoice_line_ids.with_context(check_move_validity=False).unlink()

            for line in lines:
                if not list(line.keys()) or not list(line.values()):
                    continue

                product_id = self.env['product.product'].browse(list(line.keys())[0])
                if not product_id:
                    continue
                move_line_vals = self.prepare_move_line_vals(product_id, refund_invoice, line)
                line_vals = self.env['account.move.line'].new(move_line_vals)

                # line_vals._onchange_product_id()
                line_vals = line_vals._convert_to_write(
                    {name: line_vals[name] for name in line_vals._cache})
                line_vals.update({
                    'sale_line_ids': [(6, 0, [line.get('sale_line_id')] or [])],
                    'tax_ids': [(6, 0, line.get('tax_id') or [])],
                    'quantity': list(line.values())[0],
                    'price_unit': line.get('price'),
                    # 'exclude_from_invoice_tab': False
                })
                self.env['account.move.line'].with_context(check_move_validity=False).create(line_vals)
            refund_invoice_ids_rec.append(refund_invoice.id)
        return refund_invoice_ids_rec

    def create_reverse_move_for_invoice(self, invoice_id):
        refund_obj = self.env['account.move.reversal']
        invoice_obj = self.env['account.move']
        customer_ref = ''
        if self.name:
            customer_ref += f'Refund Process of Return - {self.name}'

        invoice = invoice_obj.browse(invoice_id)

        context = {'active_ids': [invoice.id], 'active_model': 'account.move'}
        refund_process = refund_obj.with_context(context).create(
            {'reason': customer_ref, "journal_id": invoice.journal_id.id})
        refund = refund_process.reverse_moves()
        refund_invoice = refund and refund.get('res_id') and invoice_obj.browse(refund.get('res_id'))
        refund_invoice.write({'invoice_origin': invoice.name, 'return_order_id': self.id})
        return refund_invoice

    def check_and_create_refund_invoice(self, return_line_ids):
        product_process_dict = {}
        refund_invoice_ids = {}

        for line in return_line_ids:
            if self.is_approval_without_receipt and line.id not in product_process_dict:
                qty = line.quantity if line.to_be_replace_quantity <= 0 else line.to_be_replace_quantity
                product_process_dict[line.id] = {'total_qty': qty, 'invoice_line_ids': {}}

            if line.id not in product_process_dict:
                product_process_dict[line.id] = {'total_qty': line.return_qty, 'invoice_line_ids': {}}

            invoice_lines = line.stock_move_id.sale_line_id.invoice_lines
            for invoice_line in invoice_lines.filtered(
                    lambda l: l.move_id.move_type == 'out_invoice'):
                if invoice_line.move_id.state != 'posted':
                    message = _("The invoice was not posted. Please check invoice :"
                                "<a href=# data-oe-model=account.move data-oe-id=%d>%s</a>") % (
                                  invoice_line.move_id.id, invoice_line.move_id.display_name)
                    self.message_post(body=Markup(message))
                    return False

                product_line = product_process_dict.get(line.id)
                if product_line.get('process_qty', 0) < product_line.get('total_qty', 0):
                    product_line, process_qty = self.prepare_product_qty_dict(product_line, invoice_line)
                    product_line.get('invoice_line_ids').update(
                        {invoice_line.id: process_qty, 'invoice_id': invoice_line.move_id.id})
                    refund_invoice_ids = self.prepare_refund_invoice_dict(
                        line, refund_invoice_ids, invoice_line, process_qty)

        return refund_invoice_ids

    def prepare_refund_invoice_dict(self, line, refund_invoice_ids, invoice_line, process_qty):
        sale_line = line.stock_move_id.sale_line_id
        refund_invoice_vals = self.add_dict_values_for_refund_invoice(line, sale_line, invoice_line, process_qty)
        if refund_invoice_ids.get(invoice_line.move_id.id):
            refund_invoice_ids.get(invoice_line.move_id.id).append(refund_invoice_vals)
        else:
            refund_invoice_ids.update({invoice_line.move_id.id: [refund_invoice_vals]})

        return refund_invoice_ids

    @staticmethod
    def prepare_move_line_vals(product_id, refund_invoice, line):
        return {'product_id': product_id.id,
                'name': product_id.name,
                'move_id': refund_invoice.id,
                'discount': line.get('discount') or 0}

    @staticmethod
    def add_dict_values_for_refund_invoice(line, sale_line, invoice_line, process_qty):
        return {invoice_line.product_id.id: process_qty, 'price': line.buyback_cost or sale_line.price_unit,
                'tax_id': sale_line.tax_id.ids, 'discount': sale_line.discount, 'sale_line_id': sale_line.id}

    @staticmethod
    def prepare_product_qty_dict(product_line, invoice_line):
        if product_line.get('process_qty', 0) + invoice_line.quantity < product_line.get('total_qty', 0):
            process_qty = invoice_line.quantity
            product_line.update({'process_qty': product_line.get('process_qty', 0) + invoice_line.quantity})
        else:
            process_qty = product_line.get('total_qty', 0) - product_line.get('process_qty', 0)
            product_line.update({'process_qty': product_line.get('total_qty', 0)})

        return product_line, process_qty

    def create_buyback_refund(self, lines):
        if not self.sale_order_id.invoice_ids:
            message = _("The invoice was not created for Order : "
                        "<a href=# data-oe-model=sale.order data-oe-id=%d>%s</a>") % (
                          self.sale_order_id.id, self.sale_order_id.name)
            self.message_post(body=Markup(message))
            return False
        refund_invoice_ids_rec = []

        refund_invoice_ids = self.check_and_create_refund_invoice(lines)
        if not refund_invoice_ids:
            return False
        refund_invoice_ids_rec = self.prepare_and_create_refund_invoice(refund_invoice_ids, refund_invoice_ids_rec)
        if refund_invoice_ids_rec:
            self.write({'refund_invoice_ids': [(6, 0, refund_invoice_ids_rec)]})
        return True

    def copy(self, default=None):
        claim = self.browse(self.id)
        default = dict(default or {},
                       name=_('%s (copy)') % claim.name)
        res = super(SetuReturnOrder, self).copy(default)
        res.onchange_picking_id()
        return res

    def message_new(self, msg, custom_values=None):
        if custom_values is None:
            custom_values = {}
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ' '
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        if msg.get('priority'):
            defaults['priority'] = msg.get('priority')
        defaults |= custom_values
        return super(SetuReturnOrder, self).message_new(msg, custom_values=defaults)

    def message_get_suggested_recipients(self):
        recipients = super(SetuReturnOrder, self).message_get_suggested_recipients()
        try:
            for record in self:
                if record.partner_id:
                    record._message_add_suggested_recipient(recipients, partner=record.partner_id, reason=_('Customer'))
                elif record.email_from:
                    record._message_add_suggested_recipient(recipients, email=record.email_from,
                                                            reason=_('Customer Email'))
        except AccessError:
            pass
        return recipients
