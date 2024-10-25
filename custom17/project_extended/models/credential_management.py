from odoo import fields, models

class CredentialManagement(models.Model):
    _name = "credential.management"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name")
    customer_id = fields.Many2one('res.partner', string="Customer")
    username = fields.Char(string="User Name")
    serverip = fields.Char(string="Server IP")
    password = fields.Char(string="Password")
    port = fields.Char(string="Port")
    is_setucredential = fields.Boolean(string="Setu Credential")
    description = fields.Text(string="Description")
    repository_urls_ids = fields.One2many('svn.url', 'credential_mgmt_id', string="Repository Urls")
    repository_urls = fields.Char(string="Repository Urls")
    project = fields.Many2one('project.project', string="Project")
