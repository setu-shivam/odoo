from odoo import fields, models, api, _


class SetuABCSalesAnalysisBIReport(models.TransientModel):
    _name = 'setu.abc.sales.analysis.bi.report'
    _description = """It helps to organize ABC sales analysis data in listview and graphview"""
    _order = "warehouse_id, sales_amount desc"

    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    warehouse_id = fields.Many2one("stock.warehouse")
    company_id = fields.Many2one("res.company", "Company")
    sales_qty = fields.Float("Total Sales")
    sales_amount = fields.Float("Total Sales Amount")
    total_orders = fields.Float("Total Orders")
    sales_amount_per = fields.Float("Total Sales Amount (%)")
    # cum_sales_amount_per = fields.Float("Cumulative Total Sales Amount (%)")
    analysis_category = fields.Char("ABC Classification")
    wizard_id = fields.Many2one("setu.abc.sales.analysis.report")

    def action_setu_abc_analysis_bi_report(self):
        """
            Author: Kinnari Tank | Date: 11/10/24 | Task: 1000
            Purpose: User can not able to open record form view from report list view
        :return:
        """
        return {}

