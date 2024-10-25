from odoo import fields,models

class HospitalStaff(models.Model):
    _name = 'hospital.staff'
    _description='Staff Members'
    _order='name'

    name=fields.Char(string='Name',required=True,help='Name of staff member')
    # dept=fields.Many2one(string='Department',help='Department of Person')
    gender = fields.Selection(selection=[('male','Male'),('female','Female')], string='Gender')
    # type=fields.
    phone = fields.Char(string='Phone', unaccent=False)
    email = fields.Char(string='Email')
    shift=fields.Selection(string='Shift',selection=[('morning','Morning'),('night','Night')],default='morning')
    working_hours=fields.Float(string='Working Hours',help='Hours of Working')
    city_id = fields.Many2one('city', string='City')
    state_id = fields.Many2one('state', string='State')
    country_id = fields.Many2one('country', string='Country')
    salary=fields.Integer(string='Salary',help='Salary per Month(10k-30k)')

    _sql_constraints = [('salary_check','check(salary >= 10000 and salary <= 30000)','should be In between 10k to 30k')]

