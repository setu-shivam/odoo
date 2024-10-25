from odoo import fields, models


class HospitalDept(models.Model):
    _name='hospital.dept'
    _decription='Hospital Departments'


    name=fields.Char(string='Department',required=True,copy=False)
    doctor_ids=fields.One2many('hospital.doctor','dept',string='Doctors',help='Doctors From this Dept')

    _sql_constraints = [('name_unique', 'UNIQUE(name)', 'Department Already Exists')]
