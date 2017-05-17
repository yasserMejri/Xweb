# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class XField(models.Model):
	name = models.CharField(max_length=50)
	rule = models.CharField(max_length=255) # JSON formatted string for storing all regex rules.
	site_group = models.ForeignKey("UrlGroup")

	def __str__(self):
		return self.name

class UrlGroup(models.Model):
	name = models.CharField(max_length=255, unique=True)
	user = models.ForeignKey(User)

	def __str__(self):
		return self.name

class Url(models.Model):
	url = models.CharField(max_length=255)
	group = models.ForeignKey(UrlGroup)
	data = models.TextField(blank=True)

	def __str__(self):
		return self.url
