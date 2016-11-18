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
from datetime import datetime
import dateutil.parser
from django.db import connection
import time

# debug tool for query speed analysis
class debug_tool:
	# initialize a new debug tool
	def __init__(self):
		self.prints = 0
		self.start = datetime.now()
		printstatement = "debug tool instantiated: {:%Y-%m-%d %H:%M:%S.%f}".format(self.start)
		print(printstatement)
	# print the current timestamp, the number of prints done from debug, and a message
	def deprint(self, msg):
		self.prints += 1
		printstatement = "{:%Y-%m-%d %H:%M:%S.%f}".format(datetime.now())
		printstatement += " ->> Debug statement #" + str(self.prints) + "\noutput:\n" + msg
		print(printstatement)
	# print the number of prints from debug, and a message
	def deend(self):
		elap = datetime.now() - self.start
		printstatement = "{:%Y-%m-%d %H:%M:%S.%f} --> ".format(datetime.now())
		printstatement += str(self.prints) + " statements printed, " + str(elap) + " seconds elapsed since function start"
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
	# cound the buildings, roads, schools, and hospitals
	nstat = ob.values('feature_type','feature_id').aggregate( \
		Building = Sum(Case(When(tags__contains=['building'], then = 1), \
			default = 0, \
			output_field = IntegerField())), \
		Roads = Sum(Case(When((Q(tags__contains={'bridge':'yes'}) | Q(tags__contains={'tunnel':'yes'}) | \
			Q(tags__contains=['highway']) | Q(tags__contains=['tracktype'])), then = 1), \
			default = 0, \
			output_field = IntegerField())), \
		Education = Sum(Case(When((Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
        		Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
			Q(tags__contains=['music_school'])), then = 1), \
			default = 0, \
			output_field = IntegerField())), \
		Health = Sum(Case(When((Q(tags__contains=['hospital']) | Q(tags__contains=['health']) | \
			Q(tags__contains=['clinic']) | Q(tags__contains=['dentist']) | Q(tags__contains=['medical']) | \
			Q(tags__contains=['surgery'])), then = 1),
			default = 0,
			output_field = IntegerField())) )
	# count the distinct mappers
	nstat['Mappers'] = ob.values('uid').distinct().count()
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
		Buildings_start = Sum( \
			Case(When(timestamp__date__lte=start, tags__contains=['building'], then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Roads_start = Sum( \
			Case(When((Q(tags__contains={'bridge':'yes'}) | Q(tags__contains={'tunnel':'yes'}) | \
			Q(tags__contains=['highway']) | Q(tags__contains=['tracktype'])) & \
			Q(timestamp__date__lte=start), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Education_start = Sum( \
        		Case(When((Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
			Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
			Q(tags__contains=['music_school']) & Q(timestamp__date__lte=start)), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Health_start = Sum( \
			Case(When((Q(tags__contains=['hospital']) | Q(tags__contains=['health']) | \
			Q(tags__contains=['clinic']) | Q(tags__contains=['dentist']) | Q(tags__contains=['medical']) | \
			Q(tags__contains=['surgery'])) & Q(timestamp__date__lte=start), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Buildings_end = Sum( \
			Case(When(tags__contains=['building'], then = 1), \
			default = 0, \
			output_field=IntegerField())), \
        	Roads_end = Sum( \
			Case(When((Q(tags__contains={'bridge':'yes'}) | Q(tags__contains={'tunnel':'yes'}) | \
			Q(tags__contains=['highway']) | Q(tags__contains=['tracktype'])), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
       		Education_end = Sum( \
			Case(When((Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
			Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
			Q(tags__contains=['music_school'])), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Health_end = Sum( \
			Case(When((Q(tags__contains=['hospital']) | Q(tags__contains=['health']) | \
			Q(tags__contains=['clinic']) | Q(tags__contains=['dentist']) | Q(tags__contains=['medical']) | \
			Q(tags__contains=['surgery'])), then = 1), \
			default = 0, \
			output_field=IntegerField())) \
	)

	d.deprint(json.dumps(selection)) # DEBUG

	# make our json obj
	stat = {}

	stat['Selection Statistics'] = selection

	# leaderboards
	# ways
	ws = ob.filter(Q(timestamp__date__range=[start,end]) & Q(feature_type='way')).values_list('user').annotate( \
        	num=Count('user')).order_by('-num')

	# nodes
	ns = ob.filter(Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).values_list('user').annotate( \
        	num=Count('user')).order_by('-num')

	# put them in our stat object and find most freq. edited POI
	foundnodes = False
	foundways = False

	pres = [ "first", "second", "third", "fourth", "fifth" ]

	stat['Nodes'] = {}
	stat['Ways'] = {}

	for index, word in enumerate(pres):

        	# Nodes
		stat['Nodes'][word]["OSM Username"] = ns[index][0]
		stat['Nodes'][word]["Nodes"] = ns[index][1]
		stat['Nodes'][word]["Rank"] = index
		stat['Nodes'][word]['Most Frequently Edited POI'] = ob.filter(Q(user=nar[index][0][1]) & \
			Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')
		# http://stackoverflow.com/questions/12522966/django-orm-hstore-counting-unique-values-of-a-key
		if user == stat['Nodes'][word]['OSM Username']:
			stat['Nodes'][word]['highlighted'] = 1
			foundnodes = True

		d.deprint(stat['Nodes'][word])	# DEBUG

		# Ways
		stat['Ways'][word]['OSM Username'] = ws[index][0]
		stat['Ways'][word]['Ways'] = ws[index][1]
		stat['Ways'][word]['Rank'] = index
		stat['Ways'][word]['Most Frequently Edited POI'] = ob.filter(Q(user=nar[index][0][1]) & \
			Q(timestamp__date__range=[start,end]) & Q(feature_type='way')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')
		if user == stat['Ways'][word]['OSM Username']:
			stat['Ways'][word]['Highlighted'] = 1
			foundways = True

		d.deprint(stat['Ways'][word])	# DEBUG

	# user search nodes
	if user != "" and not foundnodes:

		foundnr = False
		for index, item in enumerate(ns):
			if item[index][0] == user:
				stat['Nodes']['fifth'] = {}
				stat['Nodes']['fifth']['Rank'] = index
				stat['Nodes']['fifth']['OSM Username'] = user
				stat['Nodes']['fifth']['Highlighted'] = 1
				stat['Nodes']['fifth']['Most Frequently edited POI'] = ob.filter(Q(user=user) & \
					Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).raw('''SELECT k, v, count(*) \
					as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
					as v, user, timestamp FROM populate_feature) AS t \
					WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')

				break

	# user search ways
	if user != "" and not foundways:

		foundwr = False
		for index, item in enumerate(ws):
			if item[index][0] == user:
				stat['Ways']['fifth'] = {}
				stat['Ways']['fifth']['rank'] = index
				stat['Ways']['fifth']['OSM Username'] = user
				stat['Ways']['fifth']['Highlighted'] = 1
				stat['Ways']['fifth']['Most Frequently edited POI'] = ob.filter(Q(user=user) & \
					Q(timestamp__date__range=[start,end]) & \
					Q(feature_type='way')).raw('''SELECT k, v, count(*) \
					as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
					as v, user, timestamp FROM populate_feature) AS t \
					WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')
				break

	d.deprint(json.dumps(stat))	# DEBUG
	d.deend()

	# wrap it up in a json format
	return JsonResponse(stat)
