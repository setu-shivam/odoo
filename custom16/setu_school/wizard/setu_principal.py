from odoo import fields, models

class SetuPrincipal(models.TransientModel):
    _name = 'setu.principal'

    principal_id = fields.Many2one('setu.teacher',string='Principal')

    def assign_principal(self):
        self.env['setu.school'].browse(self._context.get('active_id')).write({'principal_id': self.principal_id.id})
        return True
