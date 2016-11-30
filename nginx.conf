upstream app_server {
    server 127.0.0.1:8080 fail_timeout=0;
}

server {
	listen 80 http://139.59.37.112;
    	listen [::]:80 http://139.59.37.112 ipv6only=on;

    	root /usr/share/nginx/html;
    	index index.html index.htm;

    	client_max_body_size 4G;
    	server_name _;

	location /dailydata {
		alias /home/kll/geodjango/geodjango/static/dailydata;
	}

	location / {
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        	proxy_set_header Host $http_host;
        	proxy_redirect off;
		proxy_pass http://app_server/;
	}
}
