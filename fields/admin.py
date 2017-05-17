# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from fields import models

# Register your models here.

class Url(admin.TabularInline):
	model = models.Url

class XField(admin.TabularInline):
	model = models.XField

class UrlGroupAdmin(admin.ModelAdmin):
	inlines = [
		XField, 
		Url
	]

admin.site.register(models.UrlGroup, UrlGroupAdmin)

