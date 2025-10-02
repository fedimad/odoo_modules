/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SignatureDialog }  from "@web/core/signature/signature_dialog";

import { patch } from "@web/core/utils/patch";

import MainComponent from '@stock_barcode/components/main';


patch(MainComponent.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
    },

    onClickSignature() {
        console.log("onClickSignature called");

        const record = this.env.model?.record;

        if (!record?.id) {
            this.notification.add(_t("No picking found."), { type: "warning" });
            return;
        }

        if (record.picking_type_code !== "outgoing") {
            this.notification.add(
                _t("The signature is only available for outgoing deliveries."),
                { type: "warning" }
            );
            return;
        }

        this.dialog.add(SignatureDialog, {
            defaultName: "Signature",
            nameAndSignatureProps: { mode: "draw" },
            uploadSignature: (signature) => this.uploadSignature(record.id, signature),
        });
    },

    async uploadSignature(pickingId, signature) {
        if (!signature) {
            this.notification.add(_t("Add a signature."), { type: "warning" });
            return false;
        }
        try {
            const result = await this.orm.call("stock.picking", "action_sign_delivery", [
                [pickingId],
                signature,
            ]);
            if (result === true) {
                this.notification.add(_t("Delivery signed successfully!"), { type: "success" });
                await this.env.model.load?.();
                return true;
            }
            this.notification.add(_t("Failed to save signature."), { type: "warning" });
            return false;
        } catch (error) {
            console.error("Error saving signature:", error);
            this.notification.add(_t("Error saving signature."), { type: "danger" });
            return false;
        }
    },
});
