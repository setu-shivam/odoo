from odoo import fields, models

class SvnUrl(models.Model):
    _name = "svn.url"
    _inherit = "credential.management"

    name = fields.Char(string="Name")
    odoo_version = fields.Selection([('V11', 'V11'),
                                     ('V12', 'V12'),
                                     ('V13', 'V13'),
                                     ('V14', 'V14'),
                                     ('V15', 'V15'),
                                     ('V16', 'V16'),
                                     ('V17', 'V17'),
                                     ('V18', 'V18'),
                                     ('V19', 'V19'),
                                     ('V20', 'V20')], string="Odoo Version")
    repository_url = fields.Char(string="Repository Url")
    credential_mgmt_id = fields.Many2one('credential.management',string="Repository Urls")
    product_id = fields.Many2one('product.product',string="Product")
    project_id = fields.Many2one('project.project',string="Project")