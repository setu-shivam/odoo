from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ClaimProcessWizard(models.TransientModel):
    _name = 'claim.process.wizard'
    _description = 'Wizard to process claim lines'

    claim_line_id = fields.Many2one('setu.return.order.line', "Claim Line")
    picking_id = fields.Many2one('stock.picking')
    product_id = fields.Many2one('product.product', "Product to be Replace")
    quantity = fields.Float("Quantity")
    is_create_invoice = fields.Boolean('Create New Saleorder', readonly=True)
    reject_message_id = fields.Many2one("setu.return.order.reject", "Reject Reason")
    send_goods_back = fields.Boolean("Send Goods Back to Customer")
    hide = fields.Selection([('true', 'true'), ('false', 'false')], default='true')
    state = fields.Char()
    is_visible_goods_back = fields.Boolean()
    buyback_cost = fields.Float(string="Return Product Buyback Cost", )
    is_order_invoice = fields.Boolean(string='Order Invoice', readonly=True)
    is_create_credit_note = fields.Boolean('Create Credit Note')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id.id == self._context.get('product_id'):
            self.hide = 'true'
            self.is_create_invoice = False
        else:
            self.hide = 'false'
            self.is_create_invoice = True

    @api.model
    def default_get(self, default_fields):
        res = super(ClaimProcessWizard, self).default_get(default_fields)
        if self._context.get('active_model') == 'setu.return.order':
            claim = self.env[self._context.get('active_model')].search([('id', '=', self._context.get('active_id'))])
            res['picking_id'] = claim.return_picking_id and claim.return_picking_id.id or False
            if claim.return_picking_id:
                if claim.return_picking_id.state == 'cancel':
                    res['is_visible_goods_back'] = False
                else:
                    res['is_visible_goods_back'] = True
        else:
            line = self.env['setu.return.order.line'].search([('id', '=', self._context.get('active_id'))])
            res['claim_line_id'] = line.id
            res['state'] = line.return_order_id.state
            res['product_id'] = line.to_be_replace_product_id.id or line.product_id.id
            res['quantity'] = line.to_be_replace_quantity or line.quantity
            res['is_create_invoice'] = line.is_create_invoice
            res['buyback_cost'] = line.buyback_cost
            res['is_order_invoice'] = self.is_order_invoice = True
            if not line.return_order_id.sale_order_id.invoice_ids:
                res['is_order_invoice'] = self.is_order_invoice = False
            res['is_create_credit_note'] = line.is_create_credit_note
            if res['is_order_invoice']:
                res['is_create_credit_note'] = self.is_create_credit_note = True
        return res

    def process_refund(self):
        if not self.claim_line_id:
            return False
        self.is_create_invoice = False
        if self.product_id.id != self._context.get('product_id'):
            self.is_create_invoice = True
            if self.is_order_invoice:
                self.is_create_credit_note = True
        self.claim_line_id.write(
            {'to_be_replace_product_id': self.product_id.id, 'to_be_replace_quantity': self.quantity,
             'is_create_invoice': self.is_create_invoice, 'is_create_credit_note': self.is_create_credit_note})
        return True

    def reject_claim(self):
        return_order_line_ids = self.env['setu.return.order.line'].search(
            [('id', 'in', self.env.context.get('claim_lines'))])
        if not return_order_line_ids:
            raise UserError(_('Claim Lines not found'))
        claim = return_order_line_ids[0].return_order_id
        if claim.return_picking_id and claim.return_picking_id.state not in ['done', 'cancel']:
            raise UserError(_("Please first process Return Picking Order."))
        claim.write({'reject_message_id': self.reject_message_id.id, 'state': 'reject'})
        if self.send_goods_back:
            claim.create_return_picking(return_order_line_ids)
        claim.action_return_order_send_email()
        return True

    def process_buyback(self):
        self.is_create_invoice = True
        if not self.claim_line_id:
            return False
        self.claim_line_id.write(
            {'to_be_replace_product_id': self.product_id.id, 'to_be_replace_quantity': self.quantity,
             'is_create_invoice': self.is_create_invoice, 'buyback_cost': self.buyback_cost})
        return True
