from odoo import models, fields, api
from lxml import etree


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def compute_return_order(self):
        setu_return_order_obj = self.env['setu.return.order'].sudo()
        for order_id in self:
            return_order_ids = setu_return_order_obj.search([('stock_picking_id.sale_id', '=', order_id.id)])
            order_id.return_order_count = len(return_order_ids)

    return_order_count = fields.Integer(string='Return Order Count', compute=compute_return_order)
    return_order_id = fields.Many2one('setu.return.order', string='Return Order')

    def action_view_return_order(self):
        setu_return_order_obj = self.env['setu.return.order']
        return_order_ids = setu_return_order_obj.search([('stock_picking_id.sale_id', '=', self.id)])
        if len(return_order_ids) == 1:
            return {'name': "Return Order",
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'setu.return.order',
                    'type': 'ir.actions.act_window',
                    'res_id': return_order_ids.ids[0]}
        else:
            return {'name': "Return Order",
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'setu.return.order',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', return_order_ids.ids)]}

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super(SaleOrder, self).get_view(view_id, view_type, **options)
        if view_type in ['tree', 'form']:
            action = self._context.get('params', {}).get('action', False) or False
            if not action:
                action = self._context.get('action', False)
            action = action and self.env['ir.actions.act_window'].sudo().browse(action)
            try:
                if action and action.get_external_id() and action.get_external_id().get(action.id,
                                                                                        '') == 'setu_rma.action_rma_operations_buyback':
                    arch = res.get('arch', False)
                    if arch:
                        doc = etree.XML(arch)
                        doc.set("create", "0")
                        res['arch'] = etree.tostring(doc, encoding='unicode')
            except Exception as e:
                pass
        return res

    @api.model
    def get_views(self, views, options=None):
        context = self._context.copy() or {}
        action = options and options is not None and options.get('action_id', False) or False
        action = action and self.env['ir.actions.act_window'].sudo().browse(action)
        try:
            if action and action.get_external_id() and action.get_external_id().get(action.id,
                                                                                    '') == 'setu_rma.action_rma_operations_buyback':
                context.update({'action': action.id})
        except Exception as e:
            pass
        return super(SaleOrder, self.with_context(context)).get_views(views=views, options=options)
