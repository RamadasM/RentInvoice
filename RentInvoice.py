from flask import Flask, request, url_for, redirect, session, render_template, json, flash
from flask_session import Session
import pymongo
import cryptocode
import datetime
import pandas as pd
from datetime import date
import time
from datetime import datetime, timedelta
import random
import flash

RentInvoice = Flask(__name__)
RentInvoice.config["SESSION_PERMANENT"] = False
RentInvoice.config["SESSION_TYPE"] = "filesystem"
RentInvoice.config['SECRET_KEY'] = b'1db9a6ffaf6a8566338d6d2f8db1f812a7c23a4e25299ab6ab228a81e9cfdaf0'
Session(RentInvoice)
Session(RentInvoice)

def dbopen():
	global Invoice_dbclient, Invoice_db, Invoice_dbCollection, Invoice_Receipt, Rent_Ledger
	global Invoice_Users_Collection
	Invoice_dbclient = pymongo.MongoClient("mongodb://localhost:27017/")
	Invoice_db = Invoice_dbclient["RentalInvoiceDbClient"]
	Invoice_Users_Collection = Invoice_db["InvoiceUsersTable"]
	Invoice_dbCollection = Invoice_db["RentalInvoiceTable"]
	Invoice_Receipt = Invoice_db["InvoiceReceipt"]
	Rent_Ledger = Invoice_db["RentLedger"]

@RentInvoice.route('/afterlogin/')
def afterlogin():
		gotname = session.get("username")
		gotpassword = session.get("password")
		dbopen()
		finduser = Invoice_Users_Collection.find({"User_id" : gotname})
		finduserlist = list(finduser)
		if len(finduserlist) != 0:
			for re_cord in finduserlist:
				dbpassword = re_cord.get("User_password")
				mykey = re_cord.get("User_passkey")
				decoded = cryptocode.decrypt(dbpassword,mykey)
				if decoded == gotpassword:
					error = False
					session['error'] = error
					return redirect(url_for('rentreceipt'))
				else:
					error = True
					session['error'] = error
					return  redirect(url_for('login'))
			#endfor
		else:
			error = True
			session['error'] = error
			return redirect(url_for('login'))

@RentInvoice.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
    	session['username'] = request.form['username'] 
    	session['password'] = request.form['password']
    	return redirect(url_for('afterlogin'))
    return render_template('login.html')

def is_number(n):
	try:
		float(n)   # Type-casting the string to `float`.
				   # If string is not a valid `float`, 
				   # it'll raise `ValueError` exception
	except ValueError:
		return False
	return True

@RentInvoice.route('/invdet', methods = ['POST', 'GET'])
def invdet():
	global Invoice_dbclient, Invoice_db, Invoice_dbCollection, seltenant, selinv, premise, totalrent, invoicekey
	global Invoice_Receipt, Rent_Ledger
	if request.method == 'POST':
		rentpaid = request.form.get('rentpaid')
		if not is_number(rentpaid):
			rentpaid=0
		datereceipt = request.form.get('datereceipt')
		remarks =  request.form.get('remarks')
		tds =  request.form.get('tds')
		otherded =  request.form.get('otherded')
		if request.form['submit_button'] == 'Submit':
			now = datetime.now()
			RentReceiptDict = { 
				"TimeStamp": now, 
				"InvoiceTenantGSTKey" : invoicekey,
				"Invoice No" : selinv,
				"Tenant Name" : seltenant,
				"Premise Address" : premise,
				"RentDue" : totalrent,
				"RentReceived" : float(rentpaid),
				"ReceivedDate" : datereceipt,
				"TDS" : float(tds),
				"OtherDeductions" : float(otherded),
				"Remarks" : remarks
			}
			newdoc  = Invoice_Receipt.insert_one(RentReceiptDict)
			#update the other table too
			newdisp = float(totalrent) - float(rentpaid)
			rectquery = { "InvoiceTenantGSTKey" : invoicekey }
			newvalues = { "$set": 
									{ 
									"Received" : float(rentpaid),
									"Dispute in Credit" : newdisp,
									"Received Month" : datereceipt,
									"Receipt Narration" : remarks
									}
						}
			Invoice_dbCollection.update_one(rectquery, newvalues)
			return redirect(url_for('rentreceipt'))
		elif request.form['submit_button'] == 'Exit':
			Invoice_dbclient.close()
			retvalue = "GoodBye, Thanks for Rent Receipt Update"
			return  '%s' %retvalue
		else:
			print("none")
	return render_template('invdet.html')

@RentInvoice.route('/popinv', methods = ['POST', 'GET'])
def popinv():
	global Invoice_dbclient, Invoice_db, Invoice_dbCollection, seltenant, selinv, premise, totalrent, invoicekey
	#render_template('popinv.html')
	#print("in popinv:",seltenant)
	session['disptenant'] = seltenant
	#print("session", session['disptenant'])
	allinv = list(Invoice_dbCollection.find({"Tenant Name" : seltenant}))
	invoicelist =[]
	for rec in allinv:
		invoicelist.append(rec.get("Invoice No"))
	session['invoicelist'] = invoicelist
	#print(invoicelist)
	#print('second post')
	if request.method == 'POST':
		selinv =  request.form['invoice']
		session['invoice'] = selinv
		#print(selinv)
		findinv = list(Invoice_dbCollection.find({"Invoice No" : selinv}))
		for rec1 in findinv:
			premise = rec1.get("Premise Address")
			totalrent = rec1.get("Total Rent")
			invoicekey = rec1.get("InvoiceTenantGSTKey")
			session['premise'] = premise
			session['totalrent'] = totalrent
			return redirect(url_for('invdet'))
	return render_template('popinv.html')
	
	


@RentInvoice.route('/rentreceipt', methods = ['POST', 'GET'])
def rentreceipt():
	global Invoice_dbclient, Invoice_db, Invoice_dbCollection, seltenant
	#dbopen()
	alldoc  = list(Invoice_dbCollection.find({}))
	tenantlist = []
	for doc in alldoc:
		tenantlist.append(doc.get("Tenant Name"))
	tenantlist = sorted(set(tenantlist))
	session['tenantlist'] = tenantlist
	if request.method == 'POST':
		if request.form['submit_button'] == 'Populate Invoices':
			seltenant =  request.form['tenant']
			return redirect(url_for('popinv'))
		elif request.form['submit_button'] == 'Exit':
			Invoice_dbclient.close()
			retvalue = "GoodBye, Thanks for Rent Receipt Update"
			return  '%s' %retvalue
	return render_template('rentreceipt.html')

if __name__ == '__main__':
	RentInvoice.run(host='0.0.0.0', port=5000, debug = True)
	#RentInvoice.run(debug=True)

