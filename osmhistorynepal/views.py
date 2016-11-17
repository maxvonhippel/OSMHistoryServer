from django.shortcuts import render

import sys
import json
from django.http import JsonResponse
from django.http import HttpResponse
from django_hstore import hstore
from django_hstore.hstore import DictionaryField
from django.contrib.gis.geos import Point
from django.contrib.gis.geos import Polygon
from osmhistorynepal.models import Member, Feature # your appname.models, and your model names, here
from django.db.models import Count, Q, IntegerField, Sum, Case, When
import datetime
import dateutil.parser
from django.db import connection
import time

# debug tool for query speed analysis
class debug_tool:
	prints = 0
	def __init__(self):
		self.start = datetime.datetime.now()
		printstatement = "debug tool instantiated: " + self.start
		print(printstatement)

	def deprint(self, msg):
		prints += 1
		printstatement = datetime.datetime.now() + " ->> Debug statement #" + prints + "\noutput:" + msg
		print(printstatement)

	def deend(self):
		elap = datetime.datetime.now() - self.start
		printstatement = prints + " statements printed, " + elap + " seconds elapsed since function start"
		print(printstatement)


# returns a javascript formatted array of usernames for all of nepal
def user_names_view(request):
	c = connection.cursor()
	query = 'SELECT DISTINCT a.user FROM osmhistorynepal_feature a ORDER BY a.user ASC'
	c.execute(query)
	arr = c.fetchall()
	ret = 'usernames: ['
	for p in arr: ret += "\n" + '"' + p[0] + '",'
	ret = ret[:-1]
	ret += "\n" + ']'
	return HttpResponse(ret)


# returns a json array with metadata statistics for all of nepal for all time
def nepal_statistics_view(request):
	# get all the objects
	ob = Feature.geoobjects
	# make our json obj
	nstat = {}
	# count the distinct mappers

	# --- this could be significantly sped up by combining queries w/ aggregate, but it's not worth working on rn ----

	nstat['mappers'] = ob.values('uid').distinct().count()
	# count the distinct buildings
	nstat['buildings'] = ob.filter(tags__contains=['building']).values( \
		'feature_type','feature_id').count()
	# count the distinct roads
	nstat['roads'] = ob.filter(Q(tags__contains={'bridge':'yes'}) | Q(tags__contains={'tunnel':'yes'}) | \
        	Q(tags__contains=['highway']) | Q(tags__contains=['tracktype']) \
		).values('feature_type','feature_id').count()
	# count the distinct schools
	nstat['schools'] = ob.filter(Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
        	Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
		Q(tags__contains=['music_school'])).values('feature_type','feature_id').count()
	# count the distinct hospitals
	nstat['hospitals'] = ob.filter(Q(tags__contains=['hospital']) \
        	).values('feature_type','feature_id').count()
	# wrap it up in a json format and return it
	return JsonResponse(nstat)

# returns a json array with data on a specific area of nepal in a specific time range, optionally with extra info for a specific user
def selection_statistics_view(request, range, mn_x, mn_y, mx_x, mx_y, user):

	d = debug_tool() # DEBUG

	# parse range
	sstart,send = range.split(",") # 2007-08-29T04:08:07+05:45,2007-08-29T04:08:07+05:45
	start = dateutil.parser.parse(sstart)
	end = dateutil.parser.parse(send)
	# define our bounding box
	box = Polygon.from_bbox((mn_x, mn_y, mx_x, mx_y))
	# get all the objects
	ndtmp = Feature.geoobjects.filter(Q(point__intersects=box) & Q(feature_type='node'))
	# get the unique ids from ndtmp as strings
	strids = ndtmp.extra({'feature_id_str':"CAST(feature_id AS VARCHAR)"}).values_list('feature_id_str',flat=True).distinct()
	# combine all features containing >=1 ok members with my existing list of ok nodes
	ob = Feature.geoobjects.filter(members__ref__in=strids) | ndtmp
	# for more, see:
	# http://stackoverflow.com/questions/40585055/querying-objects-using-attribute-of-member-of-many-to-many/40602515#40602515

	selection = ob.filter(timestamp__lte=end).values('feature_type','feature_id').aggregate( \
		Buildings_start=Sum( \
			Case(When(timestamp__date__lte=start, tags__contains=['building'], then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Buildings_end=Sum( \
			Case(When(tags__contains=['building'], then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Roads_start=Sum( \
			Case(When((Q(tags__contains={'bridge':'yes'}) | Q(tags__contains={'tunnel':'yes'}) | \
			Q(tags__contains=['highway']) | Q(tags__contains=['tracktype'])) & \
			Q(timestamp__date__lte=start), then = 1), \
			default = 0,
			output_field=IntegerField())), \
        	Roads_end=Sum( \
			Case(When((Q(tags__contains={'bridge':'yes'}) | Q(tags__contains={'tunnel':'yes'}) | \
			Q(tags__contains=['highway']) | Q(tags__contains=['tracktype'])), then = 1), \
			default = 0,
			output_field=IntegerField())), \
        	Schools_start=Sum( \
        		Case(When((Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
			Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
			Q(tags__contains=['music_school']) & Q(timestamp__date__lte=start)), then = 1), \
			default = 0,
			output_field=IntegerField())), \
		Schools_end=Sum( \
			Case(When((Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
			Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
			Q(tags__contains=['music_school'])), then = 1), \
			default = 0,
			output_field=IntegerField())), \
		Hospitals_start=Sum( \
			Case(When(tags__contains=['hospital'], timestamp__date__lte=start, then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Hospitals_end=Sum( \
			Case(When(tags__contains=['hospital'], then = 1), \
			default = 0, \
			output_field=IntegerField())) \
	)

	d.deprint(selection) # DEBUG

	# make our json obj
	stat = {}

	stat['Selection Statistics'] = selection

	# leaderboards
	# ways
	ws = ob.filter(Q(timestamp__date__range=[start,end]) & Q(feature_type='way')).values_list('user').annotate( \
        	num=Count('user')).order_by('-num')
	war = [ [ ("OSM Username",ws[0][0]), ("Ways",ws[0][1]), ("Rank","first") ], \
        	[ ("OSM Username",ws[1][0]), ("Ways", ws[1][1]), ("Rank","second") ], \
		[ ("OSM Username", ws[2][0]), ("Ways", ws[1][1]), ("Rank","third")] ]

	d.deprint(war)	# debug

	# nodes
	ns = ob.filter(Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).values_list('user').annotate( \
        	num=Count('user')).order_by('-num')
	nar = [ [ ("OSM Username", ns[0][0]), ("Nodes", ns[0][1]), ("Rank", "first") ], \
        	[ ("OSM Username", ns[1][0]), ("Nodes", ns[1][1]), ("Rank", "second") ], \
		[ ("OSM Username", ns[2][0]), ("Noses", ns[1][1]), ("Rank", "third")] ]

	d.deprint(nar)	# DEBUG

	# put them in our stat object and find most freq. edited POI
	foundnodes = False
	foundways = False
	pres = [ "first", "second", "third" ]

	stat['Nodes'] = {}
	stat['Ways'] = {}

	for index, word in enumerate(pres):
        	# Nodes
		stat['Nodes'][word] = nar[index]
		stat['Nodes'][word]['Most Frequently Edited POI'] = ob.filter(Q(user=nar[index][0][1]) & \
			Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')
		# http://stackoverflow.com/questions/12522966/django-orm-hstore-counting-unique-values-of-a-key
		if user == stat['Nodes'][word]['OSM Username']:
			stat['Nodes'][word]['highlighted'] = True
			foundnodes = True

		d.deprint(stat['Nodes'][word])	# DEBUG

		# Ways
		stat['Ways'][word] = war[index]
		stat['Ways'][word]['Most Frequently Edited POI'] = ob.filter(Q(user=nar[index][0][1]) & \
			Q(timestamp__date__range=[start,end]) & Q(feature_type='way')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')
		if user == stat['Ways'][word]['OSM Username']:
			stat['Ways'][word]['highlighted'] = True
			foundways = True

		d.deprint(stat['Ways'][word])	# DEBUG

	# user search nodes
	if user != "" and not foundnodes:
        	stat['Nodes']['user']['OSM Username'] = user
		foundnr = False
		for index, item in enumerate(ns):
			if item[index][0] == user:
				stat['Nodes']['user']['rank'] = index
				foundnr = True
				break
		if not foundnr:
			stat['Nodes']['user']['rank'] = 0
		stat['Nodes']['user']['highlighted'] = True
		stat['Nodes']['user']['Most Frequently edited POI'] = ob.filter(Q(user=user) & \
		Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')

		d.deprint(stat['Nodes']['user'])	# DEBUG

	# user search ways
	if user != "" and not foundways:
        	stat['Ways']['user']['OSM Username'] = user
		foundwr = False
		for index, item in enumerate(ws):
			if item[index][0] == user:
				stat['Ways']['user']['rank'] = index
				foundwr = True
				break
		if not foundwr:
			stat['Ways']['user']['rank'] = 0
		stat['Ways']['user']['highlighted'] = True
		stat['Ways']['user']['Most Frequently edited POI'] = ob.filter(Q(user=user) & \
		Q(timestamp__date__range=[start,end]) & \
		Q(feature_type='way')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')

		d.deprint(stat['Ways']['user'])	# DEBUG

	d.deprint(stat)	# DEBUG
	d.deend()

	# wrap it up in a json format
	return JsonResponse(stat)
