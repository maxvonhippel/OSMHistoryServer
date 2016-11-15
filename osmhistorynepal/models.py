from __future__ import unicode_literals

from django.contrib.gis.db import models
from django.db.models import fields
from django_hstore import hstore

# Create your models here.

class Member(models.Model):
	ref = models.CharField(max_length=200)
	reftype = models.CharField(max_length=200)
	refrole = models.CharField(max_length=200)
	def __str__(self):
		return self.ref

class Feature(models.Model):
	feature_id = models.BigIntegerField(default=0)
	version = models.IntegerField(default=0)
	changeset = models.BigIntegerField(default=0)
	uid = models.CharField(max_length=200)
	user = models.CharField(max_length=200)
	point = models.PointField(srid=4326, geography=True, blank=True, null=True)
	geoobjects = models.GeoManager()
	timestamp = models.DateTimeField()
	tags = hstore.DictionaryField()
	tagmanager = hstore.HStoreGeoManager()
	members = models.ManyToManyField(Member)
	feature_type = models.CharField(max_length=18)

	class Meta:
		unique_together = (('feature_id', 'version', 'feature_type'),)
