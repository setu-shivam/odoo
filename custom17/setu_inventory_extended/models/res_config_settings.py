from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def_uom_id = fields.Many2one('uom.uom', default_model="product.template", string='Default UOM', readonly=False,
                                 config_parameter='product_template.def_uom_id')






