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
from django.db.models import Count, Q, IntegerField
import datetime
import dateutil.parser
from django.db import connection
import time

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
	
	starttime = time.time()
	
	# parse range
	sstart,send = range.split(",") # 2007-08-29T04:08:07+05:45,2007-08-29T04:08:07+05:45
	start = dateutil.parser.parse(sstart)
	end = dateutil.parser.parse(send)
	# define our bounding box
	box = Polygon.from_bbox((mn_x, mn_y, mx_x, mx_y))
	# get all the objects
	
	# ---------------------------- this part needs to be replaced with raw SQL if possible ----------------------------
	ndtmp = Feature.geoobjects.filter(Q(point__intersects=box) & Q(feature_type='node'))
	# get the unique ids from ndtmp as strings
	strids = ndtmp.extra({'feature_id_str':"CAST(feature_id AS VARCHAR)"}).order_by( \
		'-feature_id_str').values_list('feature_id_str',flat=True).distinct()	
	# find all members whose ref values can be found in stride
	okmems = Member.objects.filter(ref__in=strids)
	# find all features containing one or more members in the accepted members list
	relsways = Feature.geoobjects.filter(members__in=okmems)
	# combine that with my existing list of allowed member-less features
	ob = relsways | ndtmp
	# for more, see: http://stackoverflow.com/questions/40585055/querying-objects-using-attribute-of-member-of-many-to-many/40602515#40602515
	# ------------------------------------------------------------------------------------------------------------------
	
	endobtime = time.time()
	print("finished ob component in " + (endobtime - starttime))
	
	selection = ob.values('feature_type','feature_id').aggregate( \
		Buildings_start=Sum( \
			Case(When(Q(timestamp__date__lte=start) & Q(tags__contains=['building']), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Buildings_end=Sum( \
			Case(When(Q(timestamp__date__lte=end) & Q(tags__contains=['building']), then = 1), \
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
			Q(tags__contains=['highway']) | Q(tags__contains=['tracktype'])) & \
			Q(timestamp__date__lte=end), then = 1), \
			default = 0,
			output_field=IntegerField())), \
        	Schools_start=Sum( \
        		Case(When((Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
			Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
			Q(tags__contains=['music_school'])) & Q(timestamp__date__lte=start), then = 1), \
			default = 0,
			output_field=IntegerField())), \
		Schools_end=Sum( \
			Case(When((Q(tags__contains=['school']) | Q(tags__contains=['college']) | \
			Q(tags__contains=['university']) | Q(tags__contains=['kindergarten']) | \
			Q(tags__contains=['music_school'])) & Q(timestamp__date__lte=end), then = 1), \
			default = 0,
			output_field=IntegerField())), \
		Hospitals_start=Sum( \
			Case(When(Q(tags__contains=['hospital']) & Q(timestamp__date__lte=start), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
		Hospitals_end=Sum( \
			Case(When(Q(tags__contains=['hospital']) & Q(timestamp__date__lte=end), then = 1), \
			default = 0, \
			output_field=IntegerField())), \
	)
	# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ start of selection statistics ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	endselecttime = time.time()
	print("finished select component in " + (endselecttime - endobtime))

	# make our json obj
	stat = {}
	
	stat['Selection Statistics'] = selection
	
	# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ end of selection statistics ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ start of leaderboard statistics ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	# leaderboards
	# ways
	ws = ob.filter(Q(timestamp__date__range=[start,end]) & Q(feature_type='way')).values_list('user').annotate( \
        	num=Count('user')).order_by('-num')
	war = [ [ ("OSM Username",ws[0][0]), ("Ways",ws[0][1]), ("Rank","first") ], \
        	[ ("OSM Username",ws[1][0]), ("Ways", ws[1][1]), ("Rank","second") ], \
		[ ("OSM Username", ws[2][0]), ("Ways", ws[1][1]), ("Rank","third")] ]
	# nodes
	ns = ob.filter(Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).values_list('user').annotate( \
        	num=Count('user')).order_by('-num')
	nar = [ [ ("OSM Username", ns[0][0]), ("Nodes", ns[0][1]), ("Rank", "first") ], \
        	[ ("OSM Username", ns[1][0]), ("Nodes", ns[1][1]), ("Rank", "second") ], \
		[ ("OSM Username", ns[2][0]), ("Noses", ns[1][1]), ("Rank", "third")] ]
	# put them in our stat object and find most freq. edited POI
	foundnodes = False
	foundways = False
	pres = [ "first", "second", "third" ]
	
	endwartime = time.time()
	print("finished war component in " + (endwartime - endselecttime))
	
	for index in range(len(pres)):
        	# Nodes
		stat['Nodes'][pres[index]] = nar[index]
		stat['Nodes'][pres[index]]['Most Frequently Edited POI'] = ob.filter(Q(user=nar[index][0][1]) & \
			Q(timestamp__date__range=[start,end]) & Q(feature_type='node')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')
		# http://stackoverflow.com/questions/12522966/django-orm-hstore-counting-unique-values-of-a-key
		if user == stat['Nodes'][pres[index]]['OSM Username']:
			stat['Nodes'][pres[index]]['highlighted'] = True
			foundnodes = True
		# Ways
		stat['Ways'][pres[index]] = war[index]
		stat['Ways'][pres[index]]['Most Frequently Edited POI'] = ob.filter(Q(user=nar[index][0][1]) & \
			Q(timestamp__date__range=[start,end]) & Q(feature_type='way')).raw('''SELECT k, v, count(*) \
			as count FROM ( SELECT skeys(tags) AS k, svals(tags) \
			as v, user, timestamp FROM populate_feature) AS t \
			WHERE k='amenity' GROUP BY k, v ORDER BY count DESC LIMIT 1''')
		if user == stat['Ways'][pres[index]]['OSM Username']:
			stat['Ways'][pres[index]]['highlighted'] = True
			foundways = True
			
	endleadertime = time.time()
	print("finished leader component in " + (endleadertime - endwartime))
	
	# user search nodes
	if user != None and not foundnodes:
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
			
	endusernodetime = time.time()
	print("finished user nodes component in " + (endusernodetime - endleadertime))
	
	# user search ways
	if user != None and not foundways:
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
	
	enduserwaytime = time.time()
	print("finished user nodes component in " + (enduserwaytime - endusernodetime))	
	
	print("finished total view in " + (enduserwaytime - starttime))		
	# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ start of leaderboard statistics ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	# wrap it up in a json format
	return JsonResponse(stat)
