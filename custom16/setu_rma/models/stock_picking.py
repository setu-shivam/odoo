from odoo import fields, models, api
from lxml import etree


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_picking_return_count(self):
        for picking_id in self:
            return_order_ids_count = self.env['setu.return.order'].sudo().search_count(
                [('stock_picking_id', '=', picking_id.id)])
            picking_id.return_picking_count = return_order_ids_count

    def get_is_return_order(self):
        for picking_id in self:
            if picking_id.state == 'done' and picking_id.picking_type_code == 'outgoing' and picking_id.sale_id:
                picking_id.is_return_order = True
            elif picking_id.state == 'done' and picking_id.picking_type_code == "internal" and picking_id.sale_id:
                picking_id.is_return_order = True
            else:
                picking_id.is_return_order = False

    is_return_order = fields.Boolean(compute=get_is_return_order, string="Is Return Order")
    return_picking_count = fields.Integer(compute=get_picking_return_count, string='Return Order')

    return_order_id = fields.Many2one('setu.return.order', string='Return Order')
    return_sale_order_id = fields.Many2one('sale.order', string="Rma Sale Order")
    return_operation_id = fields.Many2one("setu.return.order.reason", string="RMA Operation")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self._context.get('return_order', False):
            query = """select sp.id from stock_picking sp join stock_picking_type spt on sp.picking_type_id = spt.id where sp.state = 'done' and spt.code = 'outgoing'"""
            self._cr.execute(query)
            results = self._cr.fetchall()
            picking_ids = [result_tuple[0] for result_tuple in results]
            args = [['id', 'in', list(set(picking_ids))]]
        return super(StockPicking, self).name_search(name, args=args, operator=operator, limit=limit)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super(StockPicking, self).get_view(view_id, view_type, **options)
        if view_type in ['tree', 'form']:
            action = self._context.get('params', {}).get('action', False) or False
            if not action:
                action = self._context.get('action', False)
            action = action and self.env['ir.actions.act_window'].sudo().browse(action)
            try:
                if action and action.get_external_id() and action.get_external_id().get(action.id,
                                                                                        '') == 'setu_rma.action_rma_operations_replace':
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
                                                                                    '') == 'setu_rma.action_rma_operations_replace':
                context.update({'action': action.id})
        except Exception as e:
            pass
        return super(StockPicking, self.with_context(context)).get_views(views=views, options=options)
