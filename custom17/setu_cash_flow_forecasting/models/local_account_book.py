from odoo import fields, models, api


class LocalAccountData(models.Model):
    _name = 'local.account.book'
    _description = 'Local Account Book'

    date = fields.Date(string='Date')
    account_id = fields.Many2one(comodel_name='account.account', string='Account')
    description = fields.Text(string='description')
    credit = fields.Float(string='Credit Amount')
    debit = fields.Float(string='Debit Amount')
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    company_currency_id = fields.Many2one(related='company_id.currency_id', staring='company Currency')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Accounts", copy=False)
