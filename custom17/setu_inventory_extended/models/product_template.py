from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def default_get(self,fields):
        res = super(ProductTemplate, self).default_get(fields)
        unit_id = self.env['ir.config_parameter'].get_param('product_template.def_uom_id')
        uom_bool = self.env.user.has_group('uom.group_uom')
        if unit_id and uom_bool:
            res['uom_id'] = int(unit_id)
        lot_bool = self.env.user.has_group('stock.group_production_lot')
        if lot_bool:
            res['tracking'] = 'lot'
        return res
