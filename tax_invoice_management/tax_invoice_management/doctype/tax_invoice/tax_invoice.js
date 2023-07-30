// Copyright (c) 2023, Alvin and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tax Invoice', {
	// refresh: function(frm) {

	// }
	qr: function (frm) {
		if (frm.doc.qr) {
			let qr_info = frm.doc.qr.split(",");
			frm.set_value("invoice_code", qr_info[2]);
			frm.set_value("invoice_id", qr_info[3]);
			frm.set_value("net_total_amount", qr_info[4]);
			frm.set_value("date", qr_info[5]);
			frm.refresh_field();
		}
	},
	invoice_type: function (frm) {
		if (frm.doc.invoice_type == "销项发票") {
			frm.set_value("party_type_purchase", "Customer");
			frm.set_value("party_type_sales", "Company");
			frm.set_value("party_sales", frm.doc.company);
			//get tax id info from compnay doctype
			frappe.db.get_value("Company", frm.doc.company, "tax_id").then(r => {
				frm.set_value("tax_id_sales", r.message.tax_id);
			});
			frm.set_value("party_purchase", "");
			frm.set_value("tax_id_purchase", "");
			frm.refresh_field();
		}
		else if (frm.doc.invoice_type == "进项发票") {
			frm.set_value("party_type_purchase", "Company");
			frm.set_value("party_type_sales", "Supplier");
			frm.set_value("party_purchase", frm.doc.company);
			frappe.db.get_value("Company", frm.doc.company, "tax_id").then(r => {
				frm.set_value("tax_id_purchase", r.message.tax_id);
			});
			frm.set_value("party_sales", "");
			frm.set_value("tax_id_sales", "");
			frm.refresh_field();
		}

	},
	setup: function (frm) {
		frm.set_query("party_type_purchase", function () {
			return {
				filters: {
					"name": ["in", ["Customer", "Supplier", "Company"]]
				}
			};
		});
		frm.set_query("party_type_sales", function () {
			return {
				filters: {
					"name": ["in", ["Customer", "Supplier", "Company"]]
				}
			};
		});
		//create a button to call api method to recalculate info and get the new doc info and update the frm

		frm.fields_dict['reference'].grid.get_field('reference_doctype').get_query = function (doc, cdt, cdn) {
			return {
				filters: {
					"name": ["in", ["Sales Invoice", "Purchase Invoice"]]
				}
			};
		};
		frm.fields_dict['reference'].grid.get_field('reference_name').get_query = function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					"docstatus": 1,
					"company": frm.doc.company
				}
			};
		}
	},
	party_type_purchase: function (frm) {
		if (frm.doc.party_type_purchase == "Company") {
			frm.set_value("party_purchase", frm.doc.company);
			frappe.db.get_value("Company", frm.doc.company, "tax_id").then(r => {
				frm.set_value("tax_id_purchase", r.message.tax_id);
			});
			frm.refresh_field();
		}
	},
	party_type_sales: function (frm) {
		if (frm.doc.party_type_sales == "Company") {
			frm.set_value("party_sales", frm.doc.company);
			frappe.db.get_value("Company", frm.doc.company, "tax_id").then(r => {
				frm.set_value("tax_id_sales", r.message.tax_id);
			});
			frm.refresh_field();
		}
	},
	party_purchase: function (frm) {
		if (frm.doc.party_type_purchase == "Customer") {
			frappe.db.get_value("Customer", frm.doc.party_purchase, "tax_id").then(r => {
				frm.set_value("tax_id_purchase", r.message.tax_id);
			});
			frm.refresh_field();
		}
		else if (frm.doc.party_type_purchase == "Supplier") {
			frappe.db.get_value("Supplier", frm.doc.party_purchase, "tax_id").then(r => {
				frm.set_value("tax_id_purchase", r.message.tax_id);
			});
			frm.refresh_field();
		}
	},
	party_sales: function (frm) {
		if (frm.doc.party_type_sales == "Customer") {
			frappe.db.get_value("Customer", frm.doc.party_sales, "tax_id").then(r => {
				frm.set_value("tax_id_sales", r.message.tax_id);
			});
			frm.refresh_field();
		}
		else if (frm.doc.party_type_sales == "Supplier") {
			frappe.db.get_value("Supplier", frm.doc.party_sales, "tax_id").then(r => {
				frm.set_value("tax_id_sales", r.message.tax_id);
			});
			frm.refresh_field();
		}
	},
	refresh: function (frm) {
		frm.add_custom_button(__('Recalculate'), function () {
			frappe.call({
				method: "tax_invoice_management.tax_invoice_management.doctype.tax_invoice.tax_invoice.recalculate_tax_item_and_total",
				args: {
					"doc": frm.doc
				},
				callback: function (r) {
					frappe.model.sync(r.message);
					frm.refresh();
				}
			});
		});
	}

});
