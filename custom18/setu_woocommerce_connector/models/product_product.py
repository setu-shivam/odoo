from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_woocommerce_product_count(self):
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        for product_id in self:
            woocommerce_product_variant_ids = setu_woocommerce_product_variant_obj.search(
                [('odoo_product_id', '=', product_id and product_id.id)])
            product_id.woocommerce_product_count = len(
                woocommerce_product_variant_ids) if woocommerce_product_variant_ids else 0

    woocommerce_product_count = fields.Integer(string='WooCommerce Variant Count',
                                               compute='_compute_woocommerce_product_count')
    woocommerce_image_url = fields.Char(string='Image URL', translate=True)
