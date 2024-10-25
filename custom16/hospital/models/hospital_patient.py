from odoo import fields, models


class HospitalPatient(models.Model):
    _name='hospital.patient'
    _decription='Hospital Departments'

    name=fields.Char(string='Name',required=True,copy=False)
    gender = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], string='Gender')
    address=fields.Text(string='Address')
    phone = fields.Char(string='Phone', unaccent=False)
    email = fields.Char(string='Email')
    city_id = fields.Many2one('city', string='City')
    state_id = fields.Many2one('state', string='State')
    country_id = fields.Many2one('country', string='Country')
    doctor_id=fields.Many2one('hospital.doctor',string='Doctor')
    type=fields.Selection(selection=[('opd', 'OPD'), ('ipd', 'IPD')], string='Type',default='OPD')
    date=fields.Datetime(string='Date')
