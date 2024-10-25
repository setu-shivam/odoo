from odoo import models, fields, api
from datetime import datetime
from odoo.addons.setu_ecommerce_based.wizard.setu_cron_configuration_wiz import _intervalTypes


class SetuCronConfigurationWiz(models.TransientModel):
    _inherit = "setu.cron.configuration.wiz"

    @api.onchange("multi_ecommerce_connector_id")
    def onchange_woocommerce_multi_ecommerce_connector_id(self):
        ecommerce_connector_id = self.multi_ecommerce_connector_id
        if ecommerce_connector_id.ecommerce_connector == 'woocommerce_connector':
            self.woocommerce_update_export_stock_cron_field(ecommerce_connector_id)
            self.woocommerce_update_import_order_cron_field(ecommerce_connector_id)
            self.woocommerce_update_order_status_cron_field(ecommerce_connector_id)

    def woocommerce_update_export_stock_cron_field(self, ecommerce_connector_id):
        try:
            export_inventory_stock_cron_exist = ecommerce_connector_id and self.env.ref(
                'setu_woocommerce_connector.ir_cron_auto_export_inventory_ecommerce_connector_%d' % ecommerce_connector_id.id)
        except:
            export_inventory_stock_cron_exist = False
        if export_inventory_stock_cron_exist:
            self.stock_auto_export = export_inventory_stock_cron_exist.active or False
            self.inventory_export_interval_number = export_inventory_stock_cron_exist.interval_number or False
            self.inventory_export_interval_type = export_inventory_stock_cron_exist.interval_type or False
            self.inventory_export_next_execution = export_inventory_stock_cron_exist.nextcall or False
            self.inventory_export_user_id = export_inventory_stock_cron_exist.user_id.id or False

    def woocommerce_update_import_order_cron_field(self, ecommerce_connector_id):
        try:
            import_order_cron_exist = ecommerce_connector_id and self.env.ref(
                'setu_woocommerce_connector.ir_cron_woocommerce_auto_import_order_ecommerce_connector_%d' % ecommerce_connector_id.id)
        except:
            import_order_cron_exist = False
        if import_order_cron_exist:
            self.order_auto_import = import_order_cron_exist.active or False
            self.import_order_interval_number = import_order_cron_exist.interval_number or False
            self.import_order_interval_type = import_order_cron_exist.interval_type or False
            self.import_order_next_execution = import_order_cron_exist.nextcall or False
            self.import_order_user_id = import_order_cron_exist.user_id.id or False

    def woocommerce_update_order_status_cron_field(self, ecommerce_connector_id):
        try:
            update_order_status_cron_exist = ecommerce_connector_id and self.env.ref(
                'setu_woocommerce_connector.ir_cron_woocommerce_auto_update_order_status_ecommerce_connector_%d' % ecommerce_connector_id.id)
        except:
            update_order_status_cron_exist = False
        if update_order_status_cron_exist:
            self.order_status_auto_update = update_order_status_cron_exist.active or False
            self.order_status_interval_number = update_order_status_cron_exist.interval_number or False
            self.order_status_interval_type = update_order_status_cron_exist.interval_type or False
            self.order_status_next_execution = update_order_status_cron_exist.nextcall or False
            self.order_status_user_id = update_order_status_cron_exist.user_id.id or False

    def process_cron_configuration(self):
        ecommerce_connector_id = self.multi_ecommerce_connector_id
        if ecommerce_connector_id.ecommerce_connector == 'woocommerce_connector':
            self.setup_woocommerce_inventory_export_cron(ecommerce_connector_id)
            self.setup_woocommerce_import_order_cron(ecommerce_connector_id)
            self.setup_woocommerce_update_order_status_cron(ecommerce_connector_id)
        return super(SetuCronConfigurationWiz, self).process_cron_configuration()

    def setup_woocommerce_inventory_export_cron(self, ecommerce_connector_id):
        try:
            cron_exist = self.env.ref(
                'setu_woocommerce_connector.ir_cron_auto_export_inventory_ecommerce_connector_%d' % ecommerce_connector_id.id)
        except:
            cron_exist = False
        if self.stock_auto_export:
            nextcall = datetime.now() + _intervalTypes[self.inventory_export_interval_type](
                self.inventory_export_interval_number)
            vals = self.prepare_values_for_cron(self.inventory_export_interval_number,
                                                self.inventory_export_interval_type,
                                                self.inventory_export_user_id)
            vals.update({'nextcall': self.inventory_export_next_execution or nextcall.strftime('%Y-%m-%d ''%H:%M:%S'),
                         'code': "model.cron_auto_update_stock_in_ecommerce(ctx={'multi_ecommerce_connector_id':%d})" % ecommerce_connector_id.id})
            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_cron("setu_woocommerce_connector.ir_cron_process_woocommerce_export_stock")
                name = ecommerce_connector_id.name + " : " + dict(
                    ecommerce_connector_id._fields['ecommerce_connector'].selection).get(
                    ecommerce_connector_id.ecommerce_connector) + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_auto_export_inventory_ecommerce_connector_%d' % (ecommerce_connector_id.id)
                module = 'setu_woocommerce_connector'
                self.create_ir_module_data(module, name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def setup_woocommerce_import_order_cron(self, ecommerce_connector_id):
        try:
            cron_exist = self.env.ref(
                'setu_woocommerce_connector.ir_cron_woocommerce_auto_import_order_ecommerce_connector_%d' % ecommerce_connector_id.id)
        except:
            cron_exist = False
        if self.order_auto_import:
            nextcall = datetime.now() + _intervalTypes[self.import_order_interval_type](
                self.import_order_interval_number)
            vals = self.prepare_values_for_cron(self.import_order_interval_number, self.import_order_interval_type,
                                                self.import_order_user_id)
            vals.update({'nextcall': self.import_order_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                         'code': "model.cron_auto_import_ecommerce_order_chain(ctx={'multi_ecommerce_connector_id':%d})" % ecommerce_connector_id.id})
            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_cron("setu_woocommerce_connector.ir_cron_process_woocommerce_import_orders")
                name = ecommerce_connector_id.name + " : " + dict(
                    ecommerce_connector_id._fields['ecommerce_connector'].selection).get(
                    ecommerce_connector_id.ecommerce_connector) + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_woocommerce_auto_import_order_ecommerce_connector_%d' % (ecommerce_connector_id.id)
                module = 'setu_woocommerce_connector'
                self.create_ir_module_data(module, name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def setup_woocommerce_update_order_status_cron(self, ecommerce_connector_id):
        try:
            cron_exist = self.env.ref(
                'setu_woocommerce_connector.ir_cron_woocommerce_auto_update_order_status_ecommerce_connector_%d' % ecommerce_connector_id.id)
        except:
            cron_exist = False
        if self.order_status_auto_update:
            nextcall = datetime.now() + _intervalTypes[self.order_status_interval_type](
                self.order_status_interval_number)
            vals = self.prepare_values_for_cron(self.order_status_interval_number, self.order_status_interval_type,
                                                self.order_status_user_id)
            vals.update({'nextcall': self.order_status_next_execution or nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                         'code': "model.cron_auto_update_order_status_in_ecommerce(ctx={'multi_ecommerce_connector_id':%d})" % ecommerce_connector_id.id})
            if cron_exist:
                vals.update({'name': cron_exist.name})
                cron_exist.write(vals)
            else:
                core_cron = self.check_core_cron(
                    "setu_woocommerce_connector.ir_cron_process_woocommerce_order_status_export")
                name = ecommerce_connector_id.name + " : " + dict(
                    ecommerce_connector_id._fields['ecommerce_connector'].selection).get(
                    ecommerce_connector_id.ecommerce_connector) + ' : ' + core_cron.name
                vals.update({'name': name})
                new_cron = core_cron.copy(default=vals)
                name = 'ir_cron_woocommerce_auto_update_order_status_ecommerce_connector_%d' % ecommerce_connector_id.id
                module = 'setu_woocommerce_connector'
                self.create_ir_module_data(module, name, new_cron)
        else:
            if cron_exist:
                cron_exist.write({'active': False})
        return True
