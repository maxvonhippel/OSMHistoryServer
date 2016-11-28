# import.py - Django base command written by Max von Hippel
# for Kathmandu Living Labs
# command lines should be like this:
# filepath start-date path-to-poly-file
# eg, nepal.osh.pbf 2014-12-22-03:48:01 /media/sf_SharedFolderVM/nepal.poly.txt

# this code currently untested, as of most recent change to use list of added ids for speed
# may want to make even more efficient using http://stackoverflow.com/a/17735466/1586231 in the future!

# basic python stuff
import sys
import copy
import pytz
import osmium

# django specific stuff
from datetime import datetime
from django.core.management.base import BaseCommand
from django_hstore import hstore
from django.contrib.postgres.operations import HStoreExtension
from django_hstore.hstore import DictionaryField
from django.contrib.gis.geos import Point
from django.db import migrations

# our models
from osmhistorynepal.models import Member, Feature

poly = []
plyln = 0
startdate = None

# we begin by making out poly
def init_poly(polypath):
	# we are using the global ply arr
	global plyln
	# open the file to read coords
	lns = open(polypath, "r")
	for line in lns:
		try:
			# read each set of coords as a map of X, Y
			vals = list(map(float, line.split()))
			# check that they are correctly formatted
			if len(vals) == 2:
				# add legit values to our poly arr
				poly.append((copy.deepcopy(vals[0]), copy.deepcopy(vals[1])))
				# add 1 to the number of verts in our poly
				plyln += 1
		except ValueError:
			# if something goes wrong, just skip and try next value
			continue
	# print an update on the size in verts of the poly
	print("plyln:", plyln)

# we need to check if a place is in a poly
def point_inside_poly(x, y):
	# we begin by assuming it is false
	inside = False
	# assign from the first point in the poly
	p1x, p1y = poly[0]
	# iterate over the verts in the poly
	for i in range(plyln + 1):
		# is this poly point on the "outside" of our desired point?
		p2x, p2y = poly[i % plyln]
		if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
			if p1y != p2y:
				xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
			if p1x == p2x or x < xinters:
				inside = not inside
		p1x, p1y = p2x, p2y
	# return our answer
	return inside

# parse the nodes, relations, and ways
class CounterHandler(osmium.SimpleHandler):
	# the init variables of the Counter Handler
	def __init__(self):
		osmium.SimpleHandler.__init__(self)

		self.num_n = 0 # number of nodes looked at
		self.num_r = 0 # number of relations looked at
		self.num_w = 0 # number of ways looked at
		self.num_nr = 0 # number of nodes added
		self.num_rr = 0 # number of relations added
		self.num_wr = 0 # number of ways added

		# array of all the node ids we've added
		self.nds = Feature.geoobjects.filter('feature_type'='node' \
			).extra({'feature_id_str':"CAST(feature_id AS VARCHAR)"} \
			).values_list('feature_id_str', flat=True).distinct()
		# array of all the way ids we've added
		self.wds = Feature.geoobjects.filter('feature_type'='way' \
			).values_list('feature_id', flat=True).distinct()


	# if we find a node, handle it here
	def node(self, n):
		# count how many nodes we've seen so far
		self.num_n += 1
		# print a helpful message on occaision
		if self.num_n % 1000000 == 0:
			print("nodes completed:", self.num_n)
		# we begin by presuming we won't want this node
		go = False
		try:
			go = point_inside_poly(n.location.lon, n.location.lat)
		except osmium.InvalidLocationError:
			pass
		ts = pytz.utc.localize(n.timestamp)
		# if the node is in the poly AND in the date range, we add it
		if ts > startdate and go:
			# print a helpful message
			self.num_nr += 1
				print("nodes added to database:", self.num_nr)
			# the hstore of tags for the node
			t = ''
			if n.tags:
				t = {}
				for tag in n.tags:
					t[tag.k] = tag.v
			# the empty arr of members for the node
			# honestly not completely sure if this is even necesary
			m = []
			# get or create the item, less expensive and doesn't break compared to
			# other similar strategies, according to the docs
			nf, created = Feature.geoobjects.update_or_create(
				feature_id = n.id,
				version = n.version,
				changeset = n.changeset,
				uid = n.uid,
				user = n.user,
				timestamp = ts,
				feature_type = "node"
			)
			# assign the tags and location
			nf.tags = t
			try:
				nf.point = Point(n.location.lon, n.location.lat)
			except osmium.InvalidLocationError:
				nf.point = (0, 0)
			nf.save()
			# assign the empty members var, we may not need this
			nf.members = m
			nf.save()
			# add id to the list of accepted ids for use in relation and way handles
			self.nds.append(n.id)

	# if we find a relation, handle it here
	def relation(self, r):
		# print a helpful message
		self.num_r += 1
		if self.num_r % 1000000 == 0:
			print("relations completed:", self.num_r)
		# we presume we probably won't want this relation
		go = False
		for member in r.members:
			# if at least one member is in our region, we take the whole thing
			# I believe this is called a "soft cut" strategy
			if member.ref in self.wds or (member.type == "node" and member.ref in self.nds):
					go = True;
					break;
		ts = pytz.utc.localize(r.timestamp)
		# if it is in the poly and the daterange, we continue
		if ts > startdate and go:
			# print a helpful message
			self.num_rr += 1
			if self.num_rr % 1000 == 0:
				print("relations added to database:", self.num_rr)
			# get the tags and add them
			t = ''
			if r.tags:
				t = {}
				for tag in r.tags:
					t[tag.k] = tag.v
			# create empty members list
			m = []
			# get or create relation in database
			rf, created = Feature.geoobjects.update_or_create(
				feature_id = r.id,
				version = r.version,
				changeset = r.changeset,
				uid = r.uid,
				user = r.user,
				timestamp = ts,
				feature_type = "relation"
			)
			# assign tags and build and save list of members
			rf.tags = t
			if r.members:
				for member in r.members:
					g = Member(ref = member.ref, reftyle = member.type, refrole = member.role)
					g.save()
					rf.save()
					rf.members.add(g)
			rf.save()

	# if we find a way, handle it here
	def way(self, w):
		# print a helpful message
		self.num_w += 1
		if self.num_w % 1000000 == 0 or (self.num_w % 1000 == 0 and self.num_w < 1000000) or (self.num_w % 10 == 0 and self.num_w < 200):
			print("ways completed:", self.num_w)
		# we presume that we do not want this way
		go = False
		for node in w.nodes:
			if node.ref in self.nds:
					go = True;
					break;
		ts = pytz.utc.localize(w.timestamp)
		# if it is in the poly and date range, we add it
		if ts > startdate and go:
			# print a helpful message
			self.num_wr += 1
			if self.num_wr % 1000 == 0:
				print("ways added to database:", self.num_wr)
			# get the tags and add them to the object
			t = ''
			if w.tags:
				t = {}
				for tag in w.tags:
					t[tag.k] = tag.v
			# get or create object in database
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
			# get and assign the list of members (all nodes)
			if w.nodes:
				for node in w.nodes:
					loc = ""
					# some files include lon and lat and others do not for refs
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
			# save and add id to list
			wf.save()
			wds.append(w.id)

# Base Command
class Command(BaseCommand):
	# argument parsing for command line
	def add_arguments(self, parser):
		parser.add_argument('filepath') # the file path of the file to parse
		parser.add_argument('startdate') # the start date cutoff for accepted data
		parser.add_argument('polyfile') # the file path for the .poly boundary we want

	# handle a command line execution
	def handle(self, *arge, **options):
		# define startdate as a global
		global startdate
		# parse command line args
		filename = options['filepath']
		polypath = options['polyfile']
		startdateunaware = datetime.strptime(options['startdate'], '%Y-%m-%d-%H:%M:%S')
		# add time zone so we don't have any issues w/ the zone aware stamps in osm
		startdate = startdateunaware.replace(tzinfo=pytz.UTC)
		# initialize the poly verts for comparison
		init_poly(polypath)
		# initialize the handler
		n = CounterHandler()
		# apply the file!
		n.apply_file(filename)
		print("Done!")

