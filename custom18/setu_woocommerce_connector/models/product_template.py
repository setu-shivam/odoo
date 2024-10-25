from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _compute_woocommerce_template_count(self):
        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        for template_id in self:
            woocommerce_product_template_ids = setu_woocommerce_product_template_obj.search(
                [('odoo_product_tmpl_id', '=', template_id and template_id.id)])
            template_id.woocommerce_template_count = len(
                woocommerce_product_template_ids) if woocommerce_product_template_ids else 0

    woocommerce_template_count = fields.Integer(string="Template Count", compute='_compute_woocommerce_template_count')
