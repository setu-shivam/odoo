from odoo import fields, models


class SetuAdmissionForm(models.Model):
    _name = 'setu.admission.form'
    _description = 'Admission Form model'
    _rec_name = 'student_name'

    student_name = fields.Char(string='Student Name', required=True)
    class_id = fields.Many2one('setu.class', string='Class')
    address = fields.Text(string='Address')
    email = fields.Text(string='Email')
    phone = fields.Char(string='Phone', unaccent=False)
    dob = fields.Datetime(string='Birthdate')
    state = fields.Char(string='State')

    status = fields.Selection(
        string='Status',
        selection=[('draft', 'Draft'),
                   ('confirm', 'Confirm'),
                   ('done', 'Done')],
        required=False, default='draft')
