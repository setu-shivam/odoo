from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_partner_return_order_count(self):
        setu_return_order_obj = self.env['setu.return.order'].sudo()
        for partner_id in self:
            partner_id.partner_return_order_count = setu_return_order_obj.search_count([('partner_id', '=', partner_id.id)])

    partner_return_order_count = fields.Integer(compute='get_partner_return_order_count', string='Return Order')
