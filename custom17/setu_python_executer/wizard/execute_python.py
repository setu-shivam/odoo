#-*- coding:utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


# from odoo.tools.safe_eval import safe_eval

class SetuPythonExecuter(models.Model):
    _name = "setu.python.executer"
    _description = "setu.python.executer"

    name = fields.Char(string='Name', size=1024, required=True)
    code = fields.Text(string='Python Code', required=True)
    result = fields.Text(string='Result', readonly=True)

    # def write(self, vals):
    #     id_list = [1]
    #     companies = self.env['res.company'].sudo().browse(id_list)
    #     for com in companies:
    #         self.env['setu.data.generator'].generator_data('2020-01-01', '2020-01-01', company=[com.id])
    #     return super().write(vals)

    # def write(self, vals):
    #     import random
    #     from datetime import date
    #
    #     products = self.env['product.product'].search([('id', '=', 381)])
    #     partners = self.env['res.partner'].search([], limit=1)
    #
    #     for product in products:
    #         for partner in partners:
    #             random_per = random.randint(30, 40)
    #             lead_time = random.randint(1, 7)
    #             price_amt = product.lst_price - (product.lst_price * random_per) / 100
    #             self.env['product.supplierinfo'].create({
    #                 'partner_id': partner.id,
    #                 'product_id': product.id,
    #                 'product_tmpl_id': product.product_tmpl_id.id,
    #                 'currency_id': self.env.ref('base.INR').id,
    #                 'delay': lead_time,
    #                 'price': price_amt  # Here check USD currency id
    #             })
    #             self.env['product.supplierinfo'].create({
    #                 'partner_id': partner.id,
    #                 'product_id': product.id,
    #                 'product_tmpl_id': product.product_tmpl_id.id,
    #                 'currency_id': self.env.ref('base.USD').id,
    #                 'delay': lead_time,
    #                 'price': self.env.ref('base.USD')._convert(price_amt, self.env.ref('base.INR'),
    #                                                            self.env.ref('base.main_company'), date.today())
    #             })
    #     res = super().write(vals)
    #     return res

    def execute_code(self):
        localdict = {'self': self, 'user_obj': self.env.user}
        for obj in self:
            try:
                exec(obj.code, localdict)
                if localdict.get('result', False):
                    self.write({'result': localdict['result']})
                else:
                    self.write({'result': ''})
            except Exception as e:
                raise ValidationError(_('Python code is not able to run ! message : %s' % e))

    def test(self):
        import os
        import re
        from odoo import tools
        custom_addons_path = list(
            filter(lambda x: x.__contains__('custom_addons'), tools.config['addons_path'].split(',')))
        for path in custom_addons_path:
             for module in sorted(os.listdir(str(path))):
                if module == 'aar_pos_ticket':
                    continue
                replace_fields = {}
                if not os.path.exists(os.path.join(path, module, 'models')):
                    continue
                for dir in ['models','wizard','reports', 'controllers']:
                    if not os.path.isdir(os.path.join(path, module, dir)):
                        continue
                    for file in os.listdir(os.path.join(path, module, dir)):
                        if file.startswith('__'):
                            continue
                        f = open(os.path.join(path, module, 'models', file), 'r+')
                        data = f.read()
                        table = ''
                        model = False
                        for line in data.split("\n"):
                            if re.search('_inherit.*=', line) or re.search('_name.*=', line):
                                table = line.split('=')[1].strip().replace('"', '').replace("'", '')
                            if (table and not model) or (model and table != model.model):
                                model = self.env['ir.model'].search([('model', '=ilike', table)])
                            if line.__contains__('_auto'):
                                break
                            if not re.search(".*= fields.*", line):
                                continue
                            if model:
                                field_name = line.split('=')[0].strip()
                                if field_name.startswith('x_'):
                                    continue
                                existing_field = self.env['ir.model.fields'].search(
                                    [('name', '=', field_name), ('model_id', '=', model.id)])
                                copy_data = {'name': 'x_%s' % existing_field.name}
                                if existing_field.ttype == 'selection':
                                    selection = self.env[model.model].fields_get(
                                        allfields=[field_name])[field_name]
                                    copy_data.update({'selection': str(selection)})
                                new_field = existing_field.copy(copy_data)
                                replace_fields[field_name] = new_field.name
                                if existing_field.ttype == 'one2many':
                                    continue
                                self._cr.execute(
                                    "UPDATE {0} SET {1} = {2}".format(self.env[model.model]._table, new_field.name,
                                                                      field_name))
                for root, dir, file in os.walk(os.path.join(path, module)):
                    print(file)



