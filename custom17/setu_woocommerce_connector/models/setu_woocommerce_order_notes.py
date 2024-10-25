from odoo import fields, models, api


class SetuWooCommerceOrderNotes(models.Model):
    _name = 'setu.woocommerce.order.notes'
    _description = 'WooCommerce Order Notes'

    is_customer_note = fields.Boolean(string='Is Customer Note', required=False,
                                      help="If true, the note will be shown to customers and they will be notified. "
                                           "If false, the note will be for admin reference only.")
    is_added_by_user = fields.Boolean(string="Is Added By User",
                                      help="If true, this note will be attributed to the current user. "
                                           "If false, the note will be attributed to the system.")
    note = fields.Char(string="Order Note", help="Order note content", translate=True)
    author = fields.Char(string="Author", help="Order note author.", translate=True)
    order_note_id = fields.Integer(string="Order Note ID", help="Unique identifier for the Coupons")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
