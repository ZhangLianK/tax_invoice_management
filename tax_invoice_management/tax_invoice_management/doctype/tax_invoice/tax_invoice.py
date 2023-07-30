# Copyright (c) 2023, Alvin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TaxInvoice(Document):
	def validate(self):
		if self.invoice_opening == 0:
			self.validate_reference_doc()
	def validate_reference_doc(self):
		#check if reference is empty
		if len(self.reference) == 0:
			frappe.throw("参考单据不能为空。")

		if self.invoice_type == '销项发票':
			#check doc in reference child table is sales invoice
			for reference in self.reference:
				if reference.reference_doctype != 'Sales Invoice':
					frappe.throw("发票类型为销项发票时，参考单据必须为销售费用清单。")
		elif self.invoice_type == '进项发票':
			#check doc in reference child table is purchase invoice
			for reference in self.reference:
				if reference.reference_doctype != 'Purchase Invoice':
					frappe.throw("发票类型为进项发票时，参考单据必须为采购费用清单。")
		else:
			frappe.throw("发票类型必须为销项发票或进项发票。")

		#check if refrence docs' total amount is equal to the tax invoice's grand total
		reference_total_amount = 0
		for reference in self.reference:
			#check if reference doc has been included in other tax invoice
			if frappe.db.get_value("Tax Invoice Reference", {"reference_doctype": reference.reference_doctype, "reference_name": reference.reference_name, "docstatus":1}, "name"):
				frappe.throw(f"参考单据 {reference.reference_name} 已经被使用在其他发票中。")
			
			#check if the outstanding amount is zero, otherwise throw error
			if reference.outstanding_amount != 0:
				frappe.throw(f"参考单据 {reference.reference_name} 的未付金额不为零。没有清账完毕的单据不能开票。")

			reference_total_amount += reference.total_amount
		
		if reference_total_amount != self.grand_total:
			frappe.throw(f"参考单据的总金额 {reference_total_amount} 不等于发票的总金额 {self.grand_total}。")

@frappe.whitelist()
def make_tax_invoice_from_sales_invoice(source_name):
	
	source_doc = frappe.get_doc("Sales Invoice",source_name)

	tax_invoice = frappe.new_doc("Tax Invoice")

	tax_invoice.invoice_type = '销项发票'
	tax_invoice.company = source_doc.company
	tax_invoice.tax_items = []
	tax_invoice.reference = []

	tax_invoice.party_type_purchase = 'Customer'
	tax_invoice.party_purchase = source_doc.customer
	tax_id = frappe.db.get_value("Customer", source_doc.customer, "tax_id")
	tax_invoice.tax_id_purchase = tax_id

	tax_invoice.party_type_sales = 'Company'
	tax_invoice.party_sales = source_doc.company
	tax_invoice.tax_id_sales = frappe.db.get_value("Company", source_doc.company, "tax_id")

	tax_invoice.reference_doc_type = 'Sales Invoice'
	tax_invoice.reference_doc_name = source_doc.name

	#get all return invoice doc against source_doc
	invoices_names = frappe.get_all("Sales Invoice", filters={"return_against": source_doc.name})
	invoices = []
	for invoice_name in invoices_names:
		invoices.append(frappe.get_doc("Sales Invoice", invoice_name.name))
	
	#new list to store return invoice and the source_doc
	invoices.append(source_doc)	
	
	for invoice in invoices:
		for source_item in invoice.items:
			item_tax_desc = frappe.db.get_value("Item", source_item.item_code, "tax_item_desc")
			if invoice.taxes[0].included_in_print_rate == 1:
				tax_invoice.append("tax_items",{
					"item_tax": source_item.item_code,
					"item_tax_desc": item_tax_desc,
					"qty": source_item.qty,
					"uom": source_item.uom,
					"price": source_item.net_rate,
					"amount": source_item.net_amount,
					"tax_amount": source_item.amount- source_item.net_amount,
					"tax_rate": source_doc.taxes[0].rate
				})
			else:
				tax_invoice.append("tax_items",{
					"item_tax": source_item.item_code,
					"item_tax_desc": item_tax_desc,
					"qty": source_item.qty,
					"uom": source_item.uom,
					"price": source_item.rate,
					"amount": source_item.amount,
					"tax_amount": source_item.amount * source_doc.taxes[0].rate / 100,
					"tax_rate": source_doc.taxes[0].rate
				})
			
			tax_invoice.append("reference",{
				"reference_doctype": 'Sales Invoice',
				"reference_name": invoice.name,
				"total_amount": invoice.total,
				"total_qty": invoice.total_qty,
				"status": invoice.status,
				"outstanding_amount": invoice.outstanding_amount
			})


	#sum amount and tax_amount in tax_items and calculate grand_total 
	tax_invoice.net_total_amount = sum([d.amount for d in tax_invoice.tax_items])
	tax_invoice.tax_total = sum([d.tax_amount for d in tax_invoice.tax_items])
	tax_invoice.grand_total = tax_invoice.net_total_amount + tax_invoice.tax_total

	return tax_invoice

@frappe.whitelist()
def make_tax_invoice_from_purchase_invoice(source_name):
	
	source_doc = frappe.get_doc("Purchase Invoice",source_name)

	tax_invoice = frappe.new_doc("Tax Invoice")

	tax_invoice.invoice_type = '进项发票'
	tax_invoice.company = source_doc.company
	tax_invoice.tax_items = []
	tax_invoice.reference = []
	tax_invoice.party_type_purchase = 'Company'
	tax_invoice.party_purchase = source_doc.company
	tax_id = frappe.db.get_value("Company", source_doc.company, "tax_id")
	tax_invoice.tax_id_purchase = tax_id

	tax_invoice.party_type_sales = 'Supplier'
	tax_invoice.party_sales = source_doc.supplier
	tax_invoice.tax_id_sales = frappe.db.get_value("Supplier", source_doc.supplier, "tax_id")

	tax_invoice.reference_doc_type = 'Purchase Invoice'
	tax_invoice.reference_doc_name = source_doc.name


	for source_item in source_doc.items:
		item_tax_desc = frappe.db.get_value("Item", source_item.item_code, "tax_item_desc")
		if source_doc.taxes[0].included_in_print_rate == 1:
			tax_invoice.append("tax_items",{
				"item_tax": source_item.item_code,
				"item_tax_desc": item_tax_desc,
				"qty": source_item.qty,
				"uom": source_item.uom,
				"price": source_item.net_rate,
				"amount": source_item.net_amount,
				"tax_amount": source_item.amount- source_item.net_amount,
				"tax_rate": source_doc.taxes[0].rate
			})
		else:
			tax_invoice.append("tax_items",{
				"item_tax": source_item.item_code,
				"item_tax_desc": item_tax_desc,
				"qty": source_item.qty,
				"uom": source_item.uom,
				"price": source_item.rate,
				"amount": source_item.amount,
				"tax_amount": source_item.amount * source_doc.taxes[0].rate / 100,
				"tax_rate": source_doc.taxes[0].rate
			})
		
		tax_invoice.append("reference",{
			"reference_doctype": 'Purchase Invoice',
			"reference_name": source_doc.name,
			"total_amount": source_doc.total,
			"total_qty": source_doc.total_qty,
			"status": source_doc.status,
			"outstanding_amount": source_doc.outstanding_amount
		})
	#sum amount and tax_amount in tax_items and calculate grand_total 
	tax_invoice.net_total_amount = sum([d.amount for d in tax_invoice.tax_items])
	tax_invoice.tax_total = sum([d.tax_amount for d in tax_invoice.tax_items])
	tax_invoice.grand_total = tax_invoice.net_total_amount + tax_invoice.tax_total

	return tax_invoice



@frappe.whitelist()
def recalculate_tax_item_and_total(doc):
	#generate new tax_item based on reference invoices updated by user
	doc = frappe.parse_json(doc)
	doc = frappe.get_doc(doc)
	doc.tax_items = []
	doc.net_total_amount = 0
	doc.tax_total = 0
	doc.grand_total = 0
	for reference in doc.reference:
		if doc.invoice_type == '销项发票':
			reference_doc = frappe.get_doc("Sales Invoice", reference.reference_name)
			if reference_doc:
				#check if reference doc has been included in other tax invoice
				if frappe.db.get_value("Tax Invoice Reference", {"reference_doctype": reference.reference_doctype, "reference_name": reference.reference_name, "docstatus":1}, "name"):
					frappe.throw(f"参考单据 {reference.reference_name} 已经被使用在其他发票中。")
			else :
				frappe.throw(f"参考销项单据 {reference.reference_name} 不存在。")

		elif doc.invoice_type == '进项发票':
			reference_doc = frappe.get_doc("Purchase Invoice", reference.reference_name)
			if reference_doc:
				#check if reference doc has been included in other tax invoice
				if frappe.db.get_value("Tax Invoice Reference", {"reference_doctype": reference.reference_doctype, "reference_name": reference.reference_name, "docstatus":1}, "name"):
					frappe.throw(f"参考单据 {reference.reference_name} 已经被使用在其他发票中。")
			else :
				frappe.throw(f"参考进项单据 {reference.reference_name} 不存在。")
		else:
			frappe.throw("发票类型必须为销项发票或进项发票。")

		#update doc reference child table
		reference.total_amount = reference_doc.total
		reference.total_qty = reference_doc.total_qty
		reference.status = reference_doc.status
		reference.outstanding_amount = reference_doc.outstanding_amount

		for reference_item in reference_doc.items:
			item_tax_desc = frappe.db.get_value("Item", reference_item.item_code, "tax_item_desc")
			if reference_doc.taxes[0].included_in_print_rate == 1:
				doc.append("tax_items",{
					"item_tax": reference_item.item_code,
					"item_tax_desc": item_tax_desc,
					"qty": reference_item.qty,
					"uom": reference_item.uom,
					"price": reference_item.net_rate,
					"amount": reference_item.net_amount,
					"tax_amount": reference_item.amount- reference_item.net_amount,
					"tax_rate": reference_doc.taxes[0].rate
				})
			else:
				doc.append("tax_items",{
					"item_tax": reference_item.item_code,
					"item_tax_desc": item_tax_desc,
					"qty": reference_item.qty,
					"uom": reference_item.uom,
					"price": reference_item.rate,
					"amount": reference_item.amount,
					"tax_amount": reference_item.amount * reference_doc.taxes[0].rate / 100,
					"tax_rate": reference_doc.taxes[0].rate
				})
	#sum amount and tax_amount in tax_items and calculate grand_total
	doc.net_total_amount = sum([d.amount for d in doc.tax_items])
	doc.tax_total = sum([d.tax_amount for d in doc.tax_items])
	doc.grand_total = doc.net_total_amount + doc.tax_total

	return doc
