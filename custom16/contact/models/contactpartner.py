from odoo import fields, models


class Contactpartner(models.Model):
    _name = 'contact.partner'
    _description = 'partner'
    _rec_name = 'customer'

    customer = fields.Char(string='Customer')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    gender = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], string='Gender')
    city_id = fields.Many2one('city', string='City')
    state_id = fields.Many2one('state', string='State')
    country_id = fields.Many2one('country', string='Country')
    is_partner = fields.Boolean(string='Is Partner')
    mult_city_ids = fields.Many2many('city', 'mult_city', string='Multiple Cities')
    upload_ids = fields.Many2many('ir.attachment', relation="m2m_ir_attachment_relation", column1="m2m_id",
                                  column2="attachment_id", string="Attachments")
