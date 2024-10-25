from odoo import fields, models


class SetuSchool(models.Model):
    _name = 'setu.school'
    _description = 'School model'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    street = fields.Text(string='Street')
    city_id = fields.Many2one('city', string='City')
    state_id = fields.Many2one('state', string='State')
    country_id = fields.Many2one('country', string='Country')
    zip = fields.Integer(string='Zip')
    phone = fields.Char(string='Phone', unaccent=False)
    email = fields.Char(string='Email')
    required_age = fields.Integer(string='Required Age')
    school_standard_ids = fields.Many2many('setu.standard.standard', 'school_standard_ids', string='School Standards')
    student_ids = fields.One2many("setu.student", 'school_id', string="Students")
    principal_id = fields.Many2one('setu.teacher', string='Principal', readonly=True)

    def assign_principal(self):
        action = self.env['ir.actions.act_window']._for_xml_id('setu_school.action_assign_principal')
        return action
