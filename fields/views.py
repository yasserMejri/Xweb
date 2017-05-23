# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import forms
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from wsgiref.util import FileWrapper
from django.utils.encoding import smart_str

from fields import models

import json
import csv
import os
import mimetypes

# Create your views here.

def index(request):
	return render(request, 'index.html')

def x_login(request):

	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')

		print username
		print password

		user = authenticate(request, username=username, password=password)

		print user

		if user is not None:
			login(request, user)
			return HttpResponseRedirect(reverse('database'))

	return render(request, 'login.html', {
		'form': forms.LoginForm
		})

def x_logout(request):
	logout(request)
	return HttpResponseRedirect(reverse('login'))

def x_register(request):

	print request.method

	if request.method == 'POST':
		username = request.POST.get('username')
		password = request.POST.get('password')
		email = request.POST.get('email')

		user = User(username=username, email=email)
		user.set_password(password)
		user.save()

		return HttpResponseRedirect(reverse('login'))

	return render(request, 'register.html', {
		'form': forms.RegisterForm
		})

def refresh_db(d_id):
	database = models.UrlGroup.objects.get(pk=d_id)
	d_fields = models.XField.objects.filter(site_group = database)
	d_urls = models.Url.objects.filter(group = database)
	fields = {}
	urls = {}
	data = {}
	for item in d_fields:
		fields[item.id] = {
			'name': item.name,
			'rule': item.rule
		}
	for item in d_urls:
		urls[item.id] = {
			'url': item.url,
			'data': item.data, 
			'complete': item.complete,
		}
	return fields, urls, database

@login_required
def database(request):

	msg = ''
	msg_type= 'success'

	if request.method == 'POST':

		if request.POST.get('action') == 'delete-db':
			try:
				database = models.UrlGroup.objects.get(pk=int(request.POST.get('id')))
				fields = models.XField.objects.filter(site_group=database)
				urls = models.Url.objects.filter(group=database)
				for field in fields:
					field.delete()
				for url in urls:
					url.delete()
				database.delete()
				return HttpResponse(json.dumps({
					'status': 'success'
					}))
			except:
				return HttpResponse(json.dumps({
					'status': 'error'
					}))

		if request.POST.get('action') == 'create-db':
			db_name = request.POST.get('dbname')
			try:
				db = models.UrlGroup(
					name = db_name, 
					user = request.user
					)

				db.save()
			except:
				msg = "A database with Same Name already exists! Please try with different name!"
				msg_type = 'error'

	all_dbs = models.UrlGroup.objects.filter(user=request.user)


	return render(request, 'database.html', {
		'user': request.user, 
		'all_dbs': all_dbs, 
		'msg': msg, 
		'msg_type': msg_type
		})

@login_required
def dbfields(request, id):

	msg_type = 'success'
	msg = ''

	try:
		database = models.UrlGroup.objects.get(pk=id)
	except:
		return HttpResponse("Bad Request")

	if database.user != request.user:
		return HttpResponse("404")

	if request.method == 'POST':
		if request.POST.get('action') == 'import-field':
			file = request.FILES['import-file']
			reader = csv.reader(file)
			database = models.UrlGroup.objects.get(pk=int(request.POST.get('d_id')))
			count = 0
			print "import-field"
			print reader
			rule_id = models.RuleType.objects.all()[0]
			for row in reader:
				print row
				try:
					new_field = models.XField(
						name = row[0], 
						rule = ','.join(row[1:]), 
						rule_id = rule_id,
						site_group = database
						)
					new_field.save()
					count = count + 1
				except:
					continue
			msg = "Success! " + str(count) + "field(s) have been added"
			msg_type = 'success'

		if request.POST.get('action') == 'import-url':
			file = request.FILES['import-file']
			reader = csv.reader(file)
			database = models.UrlGroup.objects.get(pk=int(request.POST.get('d_id')))
			count = 0
			for row in reader:
				try:
					new_url = models.Url(
						url = row[0], 
						group = database
						)
					new_url.save()
					count = count + 1
				except:
					continue
			msg = "Success! " + str(count) + "url(s) have been added"
			msg_type = 'success'

		if request.POST.get('action') == 'export':
			data = []
			header_fields = []
			if request.POST.get('type') == 'field':
				fields = models.XField.objects.filter(site_group = database)
				header_fields = ['name', 'rule']
				for field in fields:
					data.append([ field.name,  field.rule ])
			if request.POST.get('type') == 'url':
				urls = models.Url.objects.filter(group = database)
				header_fields = ['url']
				for url_ in urls:
					data.append([ url_.url ])
			if request.POST.get('type') == 'data':
				fields = models.XField.objects.filter(site_group = database)
				urls = models.Url.objects.filter(group = database)
				i = 0
				header_fields = ['Url']
				for field in fields:
					header_fields.append(field)
				for url_ in urls:
					try:
						raw_data = json.loads(url_.data.replace('|', '"'))
					except:
						raw_data = []
					print raw_data
					data.append([])
					data[i].append(url_.url)
					for field in fields:
						try:
							data[i].append(raw_data[str(field.id)])
						except:
							data[i].append("")
					i = i + 1

			print data

			path = smart_str(settings.PROJECT_ROOT+'/out.csv')
			with open(path, 'w') as f:
				writer = csv.writer(f)
				writer.writerow(header_fields)
				for row in data:
					print row
					writer.writerow(row)
				f.close()

			return HttpResponse(json.dumps({
				'status': 'success'
				}))

		if request.POST.get('action') == 'refresh-table':
			try:
				fields, urls, database = refresh_db(int(request.POST.get('d_id')))
				print json.dumps(fields)
				print json.dumps(urls)
				return HttpResponse(json.dumps({
					'status': 'success', 
					'fields': fields, 
					'urls': urls
					}))
			except:
				return HttpResponse(json.dumps({
					'status': 'error',
					'msg': 'in refresh-table',
					'request': request.POST
					}))
		if request.POST.get('action') == 'update-table':
			try:
				data = json.loads(request.POST.get('data'))
				print data
				for key in data:
					url_ = models.Url.objects.get(pk=int(key))
					url_.data = data[key].replace('|', '"')
					url_.save()
				return HttpResponse(json.dumps({
					'status': 'success'
					}))
			except:
				return HttpResponse(json.dumps({
					'status': 'error', 
					'request': request.POST
					}))
		# return HttpResponse(json.dumps({
		# 		'status': msg_type, 
		# 		'msg': msg
		# 	}))


	name = database.name
	fields = models.XField.objects.filter(site_group = database)
	urls = models.Url.objects.filter(group = database)

	rules = models.RuleType.objects.all()

	return render(request, 'dbfields.html', {
		'user': request.user, 
		'name': name, 
		'rules': rules, 
		'd_id': database.id, 
		'fields': fields, 
		'urls': urls, 
		'msg': msg, 
		'msg_type': msg_type
		})

@login_required
def dbdatamanage(request):
	if request.method == 'Get':
		return HttpResponse('POST required')

	database = models.UrlGroup.objects.get(pk=int(request.POST.get('d_id')))

	if request.POST.get('action') == 'get-url-data':
		try:
			url_ = models.Url.objects.get(pk=int(request.POST.get('id')))
			return HttpResponse(json.dumps({
				'status': 'success', 
				'data': url_.data
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error'
				}))
	if request.POST.get('action') == 'set-url-data':
		try:
			url_ = models.Url.objects.get(pk=int(request.POST.get('id')))
			url_.data = request.POST.get('data')
			url_.save()
			return HttpResponse(json.dumps({
				'status': 'success', 
				'data': url_.data
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error', 
				}))

@login_required
def dbfieldmanage(request):
	if request.method == 'GET':
		return HttpResponse('POST required')

	database = models.UrlGroup.objects.get(pk=int(request.POST.get('d_id')))

	if request.POST.get('action') == 'new-field':
		print request.POST
		try:
			field = models.XField(
				name = request.POST.get('name'), 
				rule = request.POST.get('rule'), 
				rule_id = models.RuleType.objects.get(pk=int(request.POST.get('rule_id'))), 
				site_group = database
				)
			field.save()
			return HttpResponse(json.dumps({
				'status': 'success', 
				'id': field.id
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error'
				}))
	if request.POST.get('action') == 'update-field':
		try:
			field = models.XField.objects.get(pk=int(request.POST.get('id')))
			field.name =request.POST.get('name')
			field.rule_id = models.RuleType.objects.get(pk=int(request.POST.get('rule_type')))
			field.rule = request.POST.get('rule')
			field.save()
			return HttpResponse(json.dumps({
				'status': 'success'
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error'
				}))

	if request.POST.get('action') == 'new-url':
		try:
			url = models.Url(
				url =request.POST.get('url'), 
				group = database
				)
			url.save()
			return HttpResponse(json.dumps({
				'status': 'success',
				'id': url.id
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error'
				}))
	if request.POST.get('action') == 'update-url':
		try:
			url = models.Url.objects.get(pk=int(request.POST.get('id')))
			url.url = request.POST.get('url')
			url.save()
			return HttpResponse(json.dumps({
				'status': 'success'
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error'
				}))

	if request.POST.get('action') == 'del-field':
		try:
			field = models.XField.objects.get(pk=int(request.POST.get('id'))).delete()
			return HttpResponse(json.dumps({
				'status': 'success'
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error'
				}))

	if request.POST.get('action') == 'del-url':
		try:
			url = models.Url.objects.get(pk=int(request.POST.get('id'))).delete()
			return HttpResponse(json.dumps({
				'status': 'success'
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error'
				}))

@login_required
def download_out(request):

	path = smart_str(settings.PROJECT_ROOT+'/out.csv')

	wrapper = FileWrapper( open( path, "r" ) )
	content_type = mimetypes.guess_type( path )[0]

	response = HttpResponse(wrapper, content_type = content_type)
	response['Content-Length'] = os.path.getsize( path ) # not FileField instance
	response['Content-Disposition'] = 'attachment; filename=%s' % smart_str( os.path.basename( path ) ) # same here

	return response	

def download_crx(request):
	path = smart_str(settings.PROJECT_ROOT+'/extension.crx')
	wrapper = FileWrapper( open( path, "r" ) )
	content_type = mimetypes.guess_type( path )[0]

	response = HttpResponse(wrapper, content_type = content_type)
	response['Content-Length'] = os.path.getsize( path ) # not FileField instance
	response['Content-Disposition'] = 'attachment; filename=%s' % smart_str( os.path.basename( path ) ) # same here

	return response	

@csrf_exempt
def api(request):

	if request.method == 'GET':
		return HttpResponse("POST requests only")

	if request.POST.get('type') == 'login':
		username = request.POST.get('username')
		password = request.POST.get('password')
		user = authenticate(request, username=username, password=password)
		if user is not None:
			dbs = models.UrlGroup.objects.filter(user=user)
			databases = [{"id":item.id, "name":item.name} for item in dbs]
			return HttpResponse(json.dumps({
				'status': 'success', 
				'databases': databases, 
				'user': user.id
				}))
		else:
			return HttpResponse(json.dumps({
				'status': 'error', 
				'msg': 'Username or password is incorrect'
				}))

	if request.POST.get('type') == 'get_this': 
		try:
			user = User.objects.get(pk=int(request.POST.get('user')))
			fields, urls, database = refresh_db(int(request.POST.get('database')))
			dm = request.POST.get('home_url').split('/')[2]
			ud = models.Url.objects.filter(url__contains = dm)
			data = [{"id":item.id, "url": item.url, "data": item.data, "data_results": item.data_results, "complete": item.complete} for item in ud]

			if len(data[0]['data']) == 0:
				data[0]['data'] = "{}";
			if len(data[0]['data_results']) == 0:
				data[0]['data_results'] = "{}"

			nxt_complete_url = ''
			nxt_url = ''
			flag = False
			for key in urls:
				if flag:
					if urls[key]['complete'] == False:
						nxt_complete_url = urls[key]['url']
						if nxt_url != '':
							break
					if nxt_url == '':
						nxt_url = urls[key]['url']
				if key == data[0]['id']:
					flag = True

			return HttpResponse(json.dumps({
				'status': 'success', 
				'fields': fields, 
				'urls': urls, 
				'data': data , 
				'nxt_url': nxt_url, 
				'nxt_complete_url': nxt_complete_url
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error',
				'msg': 'Something went wrong!', 
				'msg_type': '0', 
				'request': request.POST
				}))

	if request.POST.get('type') == 'save': 
		try:
			user = User.objects.get(pk=int(request.POST.get('user')))
			fields, urls, database = refresh_db(int(request.POST.get('database')))
			target = models.Url.objects.get(pk=int(request.POST.get('url_id')))

			data = json.loads(target.data) if len(target.data) != 0 else {}
			data_urls = json.loads(target.data_urls) if len(target.data_urls) != 0 else {}
			data_results = json.loads(target.data_results) if len(target.data_results) != 0 else {}

			field = request.POST.get('field')
			data[field] = request.POST.get('content')
			data_urls[field] = request.POST.get('home_url')
			data_results[field] = request.POST.get('result')

			target.data = json.dumps(data)
			target.data_urls = json.dumps(data_urls)
			target.data_results = json.dumps(data_results)

			target.save()
			return HttpResponse(json.dumps({
				'status': 'success', 
				}))

		except:
			return HttpResponse(json.dumps({
				'status': 'error',
				'msg': 'Something went wrong!', 
				'msg_type': '0', 
				'request': request.POST
				}))
	if request.POST.get('type') == 'completeinverse':
		try:
			target = models.Url.objects.get(pk=int(request.POST.get('id')))
			target.complete  = not target.complete
			target.save()
			return HttpResponse(json.dumps({
				'status': 'success',
				'complete': target.complete, 
				'request': request.POST
				}))
		except:
			return HttpResponse(json.dumps({
				'status': 'error',
				'msg': 'Something went wrong!', 
				'msg_type': '0', 
				'request': request.POST
				}))


	return HttpResponse(json.dumps({
		'status': 'none', 
		'request': request.POST
		}))
