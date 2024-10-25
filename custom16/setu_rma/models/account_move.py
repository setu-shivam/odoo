from odoo import fields, models, api
from lxml import etree


class AccountMove(models.Model):
    _inherit = "account.move"
    

    return_order_id = fields.Many2one('setu.return.order', string='Return Order')
    return_order_code = fields.Char(related='return_order_id.code', string='Return Order Number')

    @api.model
    def _prepare_refund(self, *args, **kwargs):
        vals = super(AccountMove, self)._prepare_refund(*args, **kwargs)
        if self.env.context.get('return_order_id'):
            vals['return_order_id'] = self.env.context['return_order_id']
        return vals

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super(AccountMove, self).get_view(view_id, view_type, **options)
        if view_type in ['tree', 'form']:
            action = self._context.get('params', {}).get('action', False) or False
            if not action:
                action = self._context.get('action', False)
            action = action and self.env['ir.actions.act_window'].sudo().browse(action)
            try:
                if action and action.get_external_id() and action.get_external_id().get(action.id,
                                                                                        '') == 'setu_rma.action_rma_operations_refund':
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
                                                                                    '') == 'setu_rma.action_rma_operations_refund':
                context.update({'action': action.id})
        except Exception as e:
            pass
        return super(AccountMove, self.with_context(context)).get_views(views=views, options=options)
