from django.shortcuts import render

import sys
import json
from django.http import JsonResponse, HttpResponse
from django_hstore import hstore
from django_hstore.hstore import DictionaryField
from django.contrib.gis.geos import Point, Polygon
from osmhistorynepal.models import Member, Feature # your appname.models, and your model names, here
from django.db.models import Count, Q, IntegerField, Sum, Case, When, Prefetch
from datetime import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
from django.utils import timezone
from django.db import connection
import time
from collections import Counter

# ---------------------------------- HELPER FUNCTIONS ---------------------------------------------

# ---------------------------------- DIFF FOR TIMESTAMPS
# http://stackoverflow.com/a/37471918/1586231
def diff(t_a, t_b):
    t_diff = relativedelta(t_a, t_b)
    return '{h}h {m}m {s}s {ss}ms'.format(h=t_diff.hours, m=t_diff.minutes, s=t_diff.seconds, ss=t_diff.microseconds)

# ---------------------------------- SIMPLE DEBUG TOOL
class debug_tool:
	# initialize a new debug tool
	def __init__(self):
		self.prints = 0
		self.start = datetime.now()
		self.last = self.start
		printstatement = "debug tool instantiated: {:%Y-%m-%d %H:%M:%S.%f}".format(self.start)
		print(printstatement)
	# print the current timestamp, the number of prints done from debug, and a message
	def deprint(self, msg):
		self.prints += 1
		now = datetime.now()
		printstatement = "{:%Y-%m-%d %H:%M:%S.%f}".format(now)
		printstatement += "\nelapsed since last: " + diff(self.last, now) + "\n"
		printstatement += " ->> Debug statement #" + str(self.prints) + "\noutput:\n" + msg + "\n"
		print(printstatement)
		self.last = now
	# print the number of prints from debug, and a message
	def deend(self):
		now = datetime.now()
		printstatement = "{:%Y-%m-%d %H:%M:%S.%f} --> ".format(now)
		printstatement += str(self.prints) + " statements printed, " + diff(self.start, now) + " seconds elapsed since function start"
		self.last = now
		print(printstatement)

# ---------------------------------- MOST FREQUENT POI FOR A USER
def most_frequent_poi(user, sen):
	return sen.raw("SELECT value as id FROM ( SELECT value, count(*) FROM ( SELECT b.feature_id, b.feature_type, b.timestamp, b.user, svals ( SLICE(b.tags, ARRAY['amenity', 'hospital', 'business', 'aerialway', 'aeroway', 'name', 'place', 'healthcare', 'barrier', 'boundary', 'building', 'craft', 'emergency', 'geological', 'highway', 'historic', 'landuse', 'type', 'leisure', 'man_made', 'military', 'natural', 'office', 'power', 'public_transport', 'railway', 'route', 'shop', 'sport', 'waterway', 'tunnel', 'service'])) AS value FROM osmhistorynepal_feature b WHERE b.user = %s ) AS stat WHERE NOT value IN ('yes', 'no', 'primary', 'secondary', 'unclassified') AND NOT value ~ '^[0-9]+$' GROUP BY value ORDER BY count DESC, value LIMIT 1 ) AS vc", user)[:1]


# ---------------------------------- TOP FIVE MOST ACTIVE USERS IN SELECTION
def top_five(user, sen):
	found = False
	ret = {}
	pres = [ "first", "second", "third", "fourth", "fifth" ]
	st = sen.raw("SELECT a.user, count(*) as id FROM osmhistorynepal_feature a GROUP BY a.user ORDER BY id LIMIT 5")
	# now we iterate
	for index, word in enumerate(pres):
        	ret[word] = {}
		ret[word]["Rank"] = index + 1
		i = 5
		cur = st[index]
		while index == 4 and not found:
			i += 1
			try:
				t = st[i]
				if t[0] == user:
					found = True
					ret[word]["Rank"] = i
					cur = t
			except: break
		usr = cur.user
		ret[word]["OSM Username"] = usr
		if ftype == 'node':
			ret[word]["Nodes"] = cur.count
		elif ftype == 'way':
			ret[word]["Ways"] = cur.count
		ret[word]['Most Frequently Edited POI'] = most_frequent_poi(nodeuser, sen)

		if user == usr:
			ret[word]['highlighted'] = 1
			found = True

	if ret == {}:
		return ""
	return ret



# ---------------------------------- ACTUAL VIEWS ---------------------------------------------

# ---------------------------------- ALL OF NEPAL USERS
def user_names_view(request):
	c = connection.cursor()
	query = 'SELECT DISTINCT a.user FROM osmhistorynepal_feature a ORDER BY a.user ASC'
	c.execute(query)
	arr = c.fetchall()
	ret = 'usernames: ['
	for p in arr: ret += "\n" + '"' + p[0].replace('"','') + '",' # fix later
	ret = ret[:-1]
	ret += "\n" + ']'
	return HttpResponse(ret)


# ---------------------------------- ALL OF NEPAL META DATA
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

# ---------------------------------- SELECTION WITHIN NEPAL, DATE RANGE META DATA
def selection_statistics_view(request, range, mn_x, mn_y, mx_x, mx_y, user):

	d = debug_tool() # DEBUG

	# parse range
	# eg 2007-08-29T04:08:07+05:45,2007-08-29T04:08:07+05:45
	sstart,send = range.split(",")
	start = dateutil.parser.parse(sstart)
	end = dateutil.parser.parse(send)
	# define our bounding box
	box = Polygon.from_bbox((mn_x, mn_y, mx_x, mx_y))
	# get all the objects
	ndtmp = Feature.geoobjects.filter(Q(feature_type='node') & Q(point__intersects=box))
	# get the unique ids from ndtmp as strings
	strids = ndtmp.extra({'feature_id_str':"CAST(feature_id AS VARCHAR)"}).values_list('feature_id_str',flat=True).distinct()
	# combine all features containing >=1 ok members with my existing list of ok nodes
	rw = Feature.geoobjects.prefetch_related(Prefetch('members', queryset=Member.objects.filter(ref__in=strids)))
	ob = rw | ndtmp

	stat = {}

	d.deprint("now time for selection")
	selection = ob.only('tags', 'timestamp', 'feature_type', 'feature_id' \
		).filter(timestamp__lte=end).values('feature_type','feature_id').aggregate( \
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
			Q(tags__contains=['music_school'])) & Q(timestamp__date__lte=start), then = 1), \
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

	stat['Selection Statistics'] = selection

	d.deprint(json.dumps(stat['Selection Statistics'])) # DEBUG

	# leaderboards

	stat['Nodes'] = {}
	stat['Ways'] = {}

	d.deprint("going to enumerate over nodes leaderboards")

	stat['Nodes'] = top_five(user, ndtmp)

	d.deprint("going to enumerate over ways leaderboards")

	stat['Ways'] = top_five(user, rw.filter(feature_type='way'))

	d.deend()

	# wrap it up in a json format
	return JsonResponse(stat)
