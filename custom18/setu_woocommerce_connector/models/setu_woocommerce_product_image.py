from odoo import fields, models, api


class SetuWooCommerceProductImage(models.Model):
    _name = 'setu.woocommerce.product.image'
    _description = 'WooCommerce Product Image'
    _order = "sequence, create_date desc, id"

    setu_woocommerce_product_image_id = fields.Char(string="WooCommerce Product Image ID")
    sequence = fields.Integer(help="Sequence of images.", index=True, default=10)
    setu_generic_product_image_id = fields.Many2one("setu.generic.product.image", string="Generic", ondelete="cascade")
    setu_woocommerce_product_variant_id = fields.Many2one("setu.woocommerce.product.variant",
                                                          string="WooCommerce Variant ID")
    setu_woocommerce_product_template_id = fields.Many2one("setu.woocommerce.product.template",
                                                           string="WooCommerce Template ID")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector')
    image = fields.Image(related="setu_generic_product_image_id.image", string="Variant Image")
    image_url = fields.Char(related="setu_generic_product_image_id.url", string="Image URL")
