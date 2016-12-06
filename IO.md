#IO for OSM History Server

We have a few distinct Views which are served over URL Schemes by Django.

* usernames
* admin
* topnodes
* jsoncountry
* jsonselection
* poinodes

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

##Admin

Example url:

> `http://139.59.37.112:8080/admin/`

Example output:

> `Server Error (500)`

Urls.py scheme:

> `url(r'^admin/', admin.site.urls),`

Obviously we are not serving any admin panel at the moment.  In the future we may want to server somthing there.

#Top Nodes

Example url:

> `http://139.59.37.112:8080/`
> 
> `2013-04-04T03:03:07,2015-04-02T05:02:04/`
> 
> `10/10/100/100/Samely/2370save/12marina9/048296609/黃靖媛/`

Example output:

Urls.py scheme:

> `url(r'^topnodes/(?P<range>([0-9T,-:+])+)/(?P<mn_x>\d+)/`
> 
> `(?P<mn_y>\d+)/(?P<mx_x>\d+)/(?P<mx_y>\d+)/(?P<first>\w+)/`
> 
> `(?P<second>\w+)/(?P<third>\w+)/(?P<fourth>\w+)/`
> 
> `(?P<fifth>\w+)/', json_views.top_five_nodes_poi),`