from odoo import api, fields, models, _
from odoo.tools.translate import _
from odoo.exceptions import UserError


class SetuReturnOrderLine(models.Model):
    _name = 'setu.return.order.line'
    _description = 'Return Order Line'

    def get_return_quantity(self):
        for record in self:
            if record.return_order_id and record.return_order_id.return_picking_id:
                move_line = self.env['stock.move'].search(
                    [('picking_id', '=', record.return_order_id.return_picking_id.id),
                     ('sale_line_id', '=', record.stock_move_id.sale_line_id.id),
                     ('product_id', '=', record.product_id.id),
                     ('origin_returned_move_id', '=', record.stock_move_id.id)])
                record.return_qty = move_line.quantity
            else:
                record.return_qty = 0

    def get_done_quantity(self):
        for record in self:
            if record.return_order_id and record.return_order_id.stock_picking_id:
                record.done_qty = record.stock_move_id.quantity
            else:
                record.done_qty = 0

    is_create_invoice = fields.Boolean(string='Create Invoice', copy=False)
    is_create_refund = fields.Boolean(string="Create Refund", copy=False)

    is_create_credit_note = fields.Boolean(string='Create Credit Note', copy=False)

    done_qty = fields.Float(string='Delivered Qty', compute=get_done_quantity)
    quantity = fields.Float(string='Requested Qty', copy=False)
    return_qty = fields.Float(string='Received Qty', compute=get_return_quantity)
    to_be_replace_quantity = fields.Float("Replace Quantity", copy=False)
    buyback_cost = fields.Float(string="Buyback cost of product", copy=False)

    return_order_type = fields.Selection(
        [('refund', 'Refund'), ('replace', 'Replace'), ('repair', 'Repair'), ('buyback', 'BuyBack')], "RMA Outcomes",
        copy=False, )

    product_id = fields.Many2one('product.product', string='Product')
    return_order_id = fields.Many2one('setu.return.order', string='Return Order', copy=False, ondelete='cascade')
    to_be_replace_product_id = fields.Many2one('product.product', "Product to be Replace", copy=False)
    stock_move_id = fields.Many2one('stock.move', string="Stock Move")
    return_order_reason_id = fields.Many2one('setu.return.order.reason', string='Customer Requested for')

    section_id = fields.Many2one(string="Sales Team", related="return_order_id.section_id")
    return_reason_id = fields.Many2one(
        comodel_name='setu.return.reason',
        string='Return Reason')

    def write(self, vals):
        for record in self:
            if record or 'return_order_reason_id' in vals:
                rma_reason = self.env['setu.return.order.reason'].browse(vals.get('return_order_reason_id'))
                if rma_reason and rma_reason.action:
                    record.return_order_type = rma_reason.action
        return super(SetuReturnOrderLine, self).write(vals)

    def unlink(self):
        for record in self:
            if record.return_order_id and record.return_order_id.state not in ['draft']:
                raise UserError(_("Return Order Line can be deleted in Draft stage only."))
        return super(SetuReturnOrderLine, self).unlink()

    def action_return_order_refund_process(self):
        return {
            'name': 'Return Products',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'claim.process.wizard',
            'src_model': 'setu.return.order.line',
            'view_id': self.env.ref('setu_rma.view_claim_picking').id,
            'target': 'new',
            'context': {'product_id': self.product_id.id, 'hide': True, 'claim_line_id': self.id}
        }

    def action_return_order_buyback_process(self):
        return {
            'name': 'BuyBack Products',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'claim.process.wizard',
            'src_model': 'setu.return.order.line',
            'view_id': self.env.ref('setu_rma.setu_view_buyback_product').id,
            'target': 'new',
            'context': {'product_id': self.product_id.id, 'hide': True, 'claim_line_id': self.id}
        }
