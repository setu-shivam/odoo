from odoo import fields, models, api, _


class SetuABCXYZAnalysisBIReport(models.TransientModel):
    _name = 'setu.abc.xyz.analysis.bi.report'
    _description = "It helps to manage abc-xyz analysis data in listview and graphview"

    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    company_id = fields.Many2one("res.company", "Company")
    sales_qty = fields.Float("Total Sales")
    sales_amount = fields.Float("Total Sales Amount")
    sales_amount_per = fields.Float("Total Sales Amount (%)")
    # cum_sales_amount_per = fields.Float("Cum. Total Sales Amount (%)")
    abc_classification = fields.Char("ABC Classification")
    current_stock = fields.Float("Current Stock")
    stock_value = fields.Float("Stock Value")
    xyz_classification = fields.Char("XYZ Classification")
    combine_classification = fields.Char("ABC-XYZ Classification")
    wizard_id = fields.Many2one("setu.abc.xyz.analysis.report")
    total_orders = fields.Float()

    def action_setu_abc_xyz_analysis_bi_report(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: User can not able to open record form view from report list view
        :return:
        """
        return {}