odoo.define('import_purchase_sale_order_xls.import_bc', function (require){
"use strict";
 
 
var core = require('web.core');
var ListView = require('web.ListView');
var QWeb = core.qweb;
 
 
ListView.include({       
     
        render_buttons: function($node) {
                var self = this;
                this._super($node);
                    this.$buttons.find('.o_import_bc_xls').click(this.proxy('wizard_import_purchase_order'));
                    this.$buttons.find('.o_import_dv_xls').click(this.proxy('wizard_import_sale_order'));
        },
 
        wizard_import_purchase_order: function () {           

        this.do_action({
                name: 'Import RFQ (code, quantity, price) .XLS(x)',

                type: 'ir.actions.act_window',

                res_model: 'wizard.import.purchase.order',

                view_mode: 'form',

                view_type: 'form',

                views: [[false, 'form']],

                target: 'new',

                context:{}                 

        });
        return { 'type': 'ir.actions.act_window',
                 'tag': 'reload',
             } 
         },

       wizard_import_sale_order: function () {           

        this.do_action({
                name: 'Import quotation (code, quantity, price) .XLS(x)',

                type: 'ir.actions.act_window',

                res_model: 'wizard.import.sale.order',

                view_mode: 'form',

                view_type: 'form',

                views: [[false, 'form']],

                target: 'new',

                context:{}                 

        });
        return { 'type': 'ir.actions.act_window',
                 'tag': 'reload',
             } 
         } 



});
 
});