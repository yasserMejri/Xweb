# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import forms
from django.contrib.auth.models import User

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

	if request.method == 'POST':
		if request.POST.get('action') == 'import-field':
			file = request.FILES['import-file']
			reader = csv.reader(file)
			database = models.UrlGroup.objects.get(pk=int(request.POST.get('d_id')))
			count = 0
			for row in reader:
				try:
					new_field = models.XField(
						name = row[0], 
						rule = row[1], 
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
			msg = "Success! " + str(count) + "field(s) have been added"
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
				database = models.UrlGroup.objects.get(pk=int(request.POST.get('d_id')))
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
						'data': item.data
					}
				print fields
				print urls
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


	name = database.name
	fields = models.XField.objects.filter(site_group = database)
	urls = models.Url.objects.filter(group = database)

	return render(request, 'dbfields.html', {
		'user': request.user, 
		'name': name, 
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
