odoo.define('sale_order_barcode.SaleBarcodeHandler', function (require) {
    "use strict";
    var core = require('web.core');
    var Model = require('web.Model');
    var FormViewBarcodeHandler = require('barcodes.FormViewBarcodeHandler');
    var SaleBarcodeHandler = FormViewBarcodeHandler.extend({
        init: function (parent) {
            if (parent.ViewManager.action) {
                this.form_view_initial_mode = parent.ViewManager.action.context.form_view_initial_mode;
            } else if (parent.ViewManager.view_form) {
                this.form_view_initial_mode = parent.ViewManager.view_form.options.initial_mode;
            }
            this.m2x_field = 'pack_operation_product_ids';
            this.quantity_field = 'qty_done';
            return this._super.apply(this, arguments);
        },
        start: function () {
            this._super();
            this.so_model = new Model("sale.order");
            this.form_view.options.disable_autofocus = 'true';
            if (this.form_view_initial_mode) {
                this.form_view.options.initial_mode = this.form_view_initial_mode;
            }
        },
        on_barcode_scanned: function(barcode) {
            var self = this;
            var so_id = self.view.datarecord.id;
            self.so_model.call('so_barcode',[barcode, so_id]).then(function () {
                self.getParent().reload();
            });
        },
    });
    core.form_widget_registry.add('sale_barcode_handler', SaleBarcodeHandler);
    return SaleBarcodeHandler;
});
