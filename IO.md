#IO for OSM History Server

We have a few distinct Views which are served over URL Schemes by Django.

* usernames
* admin
* topnodes
* jsoncountry
* jsonselection

##Usernames

Example url:

> `http://139.59.37.112:8080/usernames/`

Example output:

> `var usernames = [ "にゃー", "ねこ☆", "ばんの", "윤오리", "じょーり", "まるさん",` 
> 
> `"トリコラ", "ノンノノ", "㌔㍉ｺﾝ", "ちばていこ", "み―まー・マッククマーク",` 
> 
> `"0109", "048", "048296609", "0815-Student", "12marina9", "13bzhang",`
> 
> `"13scoter", "14riesma", "14rkarls", "19alimk", "1ambodo", "2015cfelicia",` 
> 
> `"2015ekrombee", "2015rarens", "2121vijay(Adyota)", "2370save", "24367dfa",` 
> 
> `"266", "2tug4bug", "314", "3tom", "402315", "404era", "42429", "448", ... "黃偵祐", "黃靖媛", "點點點" ];`

Urls.py scheme:

> `url(r'^usernames/', json_views.user_names_view),`

Time: ~ 5 to 15 seconds

##Admin

Example url:

> `http://139.59.37.112:8080/admin/`

Example output:

> `Server Error (500)`

Urls.py scheme:

> `url(r'^admin/', admin.site.urls),`

Time: ~ 0 to 5 seconds

Obviously we are not serving any admin panel at the moment.  In the future we may want to server somthing there.

#Top Nodes

Example url:

> `http://139.59.37.112:8080/`
> 
> `2000-04-04T03:03:07,2016-04-02T05:02:04/`
> 
> `10/10/100/100/Samely/2370save/12marina9/048296609/黃靖媛/`

Example output:

> `{"\u9ec3\u9756\u5a9b": "none", "samely": "crossing",`
> 
>  `"048296609": "none", "12marina9": "none", "2370save": "none"}`

Urls.py scheme:

> `url(r'^topnodes/(?P<range>([0-9T,-:+])+)/(?P<mn_x>\d+)/`
> 
> `(?P<mn_y>\d+)/(?P<mx_x>\d+)/(?P<mx_y>\d+)/(?P<first>\w+)/`
> 
> `(?P<second>\w+)/(?P<third>\w+)/(?P<fourth>\w+)/`
> 
> `(?P<fifth>\w+)/', json_views.top_five_nodes_poi),`

Time: ~ 20 to 100 seconds (only a couple tests, could be much more in edge cases or something, not sure yet)

#Json Country

Example url:

> `http://139.59.37.112:8080/jsoncountry`

Example output:

> `{"Education": 1, "Health": 9, "Building": 22560,`
> 
> `"Mappers": 9465, "Roads": 2512}`

Urls.py scheme:

> `url(r'^jsoncountry/', json_views.nepal_statistics_view),`

Time: ~ 10 to 45 seconds

#Json Selection

Example url:

> `http://139.59.37.112:8080/jsonselection/`
> 
> `2000-04-04T03:03:07,2016-04-02T05:02:04/0/0/100/100//`

Example output:

> `{"Health_end": 0, "Roads_end": 2378, "Education_end": 1,`
> 
> `"Buildings_start": 0, "Roads_start": 0, "Education_start": 0,`
> 
> `"Buildings_end": 22433, "Health_start": 0}`

Urls.py scheme:

> `url(r'^jsonselection/(?P<timerange>([0-9T,-:+])+)/`
> 
> `(?P<mn_x>\d+)/(?P<mn_y>\d+)/(?P<mx_x>\d+)/(?P<mx_y>\d+)/`
> 
> `(?P<user>\w+)/', json_views.selection_statistics_view),`

Time: ~ 68 seconds