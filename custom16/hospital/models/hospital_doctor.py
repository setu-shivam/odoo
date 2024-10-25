from odoo import fields, models, api
from odoo.exceptions import ValidationError


class HospitalDoctor(models.Model):
    _name = 'hospital.doctor'
    _description = 'All Doctor'
    # _order = 'name'  # type

    name = fields.Char(string='Name', help='Name of Doctors')
    code = fields.Char(string='Code', help='unique Code')
    dept = fields.Many2one('hospital.dept', string='Department', help='Department of Doctor')
    gender = fields.Selection(selection=[('male', 'Male'), ('female', 'Female')], string='Gender')
    phone = fields.Char(string='Phone', unaccent=False)
    email = fields.Char(string='Email')
    shift = fields.Selection(string='Shift', selection=[('morning', 'Morning'), ('night', 'Night')], default='morning')
    type = fields.Selection(selection=[('permanent', 'Permanent'), ('visiting', 'Visiting')], string='Type',
                            default='permanent')
    city_id = fields.Many2one('city', string='City')
    state_id = fields.Many2one('state', string='State')
    country_id = fields.Many2one('country', string='Country')
    surgeon = fields.Boolean(string='Surgeon')
    avl = fields.Boolean(string='Availability')

    # _sql_constraints = [('code_unique', 'unique(code)', 'Use different Code'),('name_check', 'CHECK(name IS NOT NULL and code IS NOT NULL)', 'Name and Code field cant be Empty')]

    # @api.model
    # def create(self, vals):
    #     if vals.get('email') == False:
    #         vals.update({'email': 'abc@hospital.mail'})
    #     return super(HospitalDoctor, self).create(vals)
    #
    #     res = super(HospitalDoctor, self).create(vals)
    #     for record in res:
    #         email=record.email
    #     return res

    # -------------------------------------------

    @api.constrains('code')
    def code_uniq(self):
        for rec in self:
            ext = self.search([('ccustomize the look of your quotations.ode', '=ilike', rec.code), ('id', '!=', rec.id)])
            if (ext):
                raise ValidationError("Code Already Exists")

    @api.model
    def create(self,vals):
        res = super(HospitalDoctor, self).create(vals)
        if res.email == False:
            res.email ='abccreate@hospital.mail'
        return res

    def write(self, vals):
        if self.email == False and not vals.get('email'):               #and/or
            vals.update({'email': 'abcwrite@hospital.mail'})
        return super(HospitalDoctor, self).write(vals)

    # @api.model
    # def default_get(self,fields):
    #     res = super(HospitalDoctor,self).default_get(fields)
    #     res['email']='default@hospital.mail'
    #     return res

    def copy(self, default=None):
        default = dict(default or {})
        default.update(name= ("%s (copy)") % self.name)
        default.update(code='')
        return super().copy(default)
