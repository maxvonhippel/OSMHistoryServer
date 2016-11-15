# import.py - Django base command written by Max von Hippel
# for Kathmandu Living Labs
# command lines should be like this:
# filepath start-date path-to-poly-file
# eg, nepal.osh.pbf 2014-12-22-03:48:01 /media/sf_SharedFolderVM/nepal.poly.txt

import sys
import copy
import pytz
import osmium

from datetime import datetime
from django.core.management.base import BaseCommand
from django_hstore import hstore
from django.contrib.postgres.operations import HStoreExtension
from django_hstore.hstore import DictionaryField
from django.contrib.gis.geos import Point
from django.db import migrations
from osmhistorynepal.models import Member, Feature

poly = []
plyln = 0
startdate = None

# we begin by making out poly
def init_poly(polypath):
	global plyln
	lns = open(polypath, "r")
	for line in lns:
		try:
			vals = list(map(float, line.split()))
			if len(vals) == 2:
				poly.append((copy.deepcopy(vals[0]), copy.deepcopy(vals[1])))
				plyln += 1
		except ValueError:
			continue
	print("plyln:", plyln)

# we need to check if a place is in a poly
def point_inside_poly(x, y):
	inside = False
	p1x, p1y = poly[0]
	for i in range(plyln + 1):
		p2x, p2y = poly[i % plyln]
		if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
			if p1y != p2y:
				xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
			if p1x == p2x or x < xinters:
				inside = not inside
		p1x, p1y = p2x, p2y
	return inside

# parse the nodes, relations, and ways
class CounterHandler(osmium.SimpleHandler):
	def __init__(self):
		osmium.SimpleHandler.__init__(self)
		self.num_n = 0
		self.num_r = 0
		self.num_w = 0
		self.num_nr = 0
		self.num_rr = 0
		self.num_wr = 0
#	def node(self, n):
#		self.num_n += 1
#		if self.num_n % 1000000 == 0:
#			print("nodes completed:", self.num_n)
#		go = False
#		try:
#			go = point_inside_poly(n.location.lon, n.location.lat)
#		except osmium.InvalidLocationError:
#			pass
#		ts = pytz.utc.localize(n.timestamp)
#		if ts > startdate and go:
#			self.num_nr += 1
#				print("nodes added to database:", self.num_nr)
#			t = ''
#			if n.tags:
#				t = {}
#				for tag in n.tags:
#					t[tag.k] = tag.v
#			m = []
#				feature_id = n.id,
#				version = n.version,
#				changeset = n.changeset,
#				uid = n.uid,
#				user = n.user,
#				timestamp = ts,
#				feature_type = "node"
#			)
#			nf.tags = t
#			try:
#				nf.point = Point(n.location.lon, n.location.lat)
#			except osmium.InvalidLocationError:
#				nf.point = (0, 0)
#			nf.save()
#			nf.members = m
#			nf.save()

#	def relation(self, r):
#		self.num_r += 1
#		if self.num_r % 1000000 == 0:
#			print("relations completed:", self.num_r)
#		go = False
#		try:
#			for member in r.members:
#				if member.type == "node":
#					inside = None
#					try:
#						inside = Feature.geobjects.get(version=1,feature_id=node.ref,feature_type='node')
#					except Feature.DoesNotExist:
#						inside = None
#					if inside != None:
#						go = True
#						break
#		except osmium.InvalidLocationError:
#			pass
#		ts = pytz.utc.localize(r.timestamp)
#			self.num_rr += 1
#			if self.num_rr % 1000 == 0:
#				print("relations added to database:", self.num_rr)
#			t = ''
#			if r.tags:
#				t = {}
#				for tag in r.tags:
#					t[tag.k] = tag.v
#			m = []
#			rf, created = Feature.geoobjects.update_or_create(
#				feature_id = r.id,
#				version = r.version,
#				changeset = r.changeset,
#				uid = r.uid,
#				user = r.user,
#				timestamp = ts,
#				feature_type = "relation"
#			)
#			rf.tags = t
#			if r.members:
#				for member in r.members:
#					g = Member(ref = member.ref, reftyle = member.type, refrole = member.role)
#					g.save()
#					rf.save()
#					rf.members.add(g)
#			rf.save()
	def way(self, w):
		self.num_w += 1
		if self.num_w % 1000000 == 0 or (self.num_w % 1000 == 0 and self.num_w < 1000000) or (self.num_w % 10 == 0 and self.num_w < 200):
			print("ways completed:", self.num_w)
		go = False
		inside = None
		for node in w.nodes:
			try:
				inside = Feature.geoobjects.get(version=1,feature_id=node.ref,feature_type='node')
			except Feature.DoesNotExist:
				inside = None
			if inside != None:
				go = True
				break
		ts = pytz.utc.localize(w.timestamp)
		if ts > startdate and go:
			self.num_wr += 1
			if self.num_wr % 1000 == 0:
				print("ways added to database:", self.num_wr)
			t = ''
			if w.tags:
				t = {}
				for tag in w.tags:
					t[tag.k] = tag.v
			wf, created = Feature.geoobjects.update_or_create(
				feature_id = w.id,
				version = w.version,
				changeset = w.changeset,
				uid = w.uid,
				user = w.user,
				timestamp = ts,
				feature_type = "way"
			)
			wf.tags = t
			if w.nodes:
				for node in w.nodes:
					loc = ""
					try:
						loc = str(node.location.lon) + "," + str(node.location.lat)
					except osmium.InvalidLocationError:
						loc = "0,0"
					g = Member(ref = node.ref, \
						reftype = "node", \
						refrole = loc)
					g.save()
					wf.save()
					wf.members.add(g)
			wf.save()

# Base Command
class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument('filepath')
		parser.add_argument('startdate')
		parser.add_argument('polyfile')
	def handle(self, *arge, **options):
		global startdate
		filename = options['filepath']
		polypath = options['polyfile']
		startdateunaware = datetime.strptime(options['startdate'], '%Y-%m-%d-%H:%M:%S')
		startdate = startdateunaware.replace(tzinfo=pytz.UTC)
		init_poly(polypath)
		n = CounterHandler()
		n.apply_file(filename)
		print("Done!")

