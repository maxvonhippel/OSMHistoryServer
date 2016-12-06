#!/bin/bash
# make the csv file of all the daily activity for the dy chart
psql nepaldata -c "VACUUM (VERBOSE, ANALYZE) osmhistorynepal_feature;";
psql nepaldata -c "\COPY ( SELECT timestamp::date AS day, SUM(CASE WHEN version = '1' THEN 1 ELSE 0 END) AS New_Features, SUM(CASE WHEN version != '1' THEN 1 ELSE 0 END) AS Edits FROM osmhistorynepal_feature GROUP BY day ) TO '/var/www/html/NepalOSMHistory/data/sampledaily/activity.csv' WITH CSV DELIMITER ','"
# make the csv file of all the node locations for the cluster map
psql nepaldata -c "VACUUM (VERBOSE, ANALYZE) osmhistorynepal_feature;";
psql nepaldata -c "\COPY ( SELECT a.feature_id, AVG(ST_X(a.point::geometry)), AVG(ST_Y(a.point::geometry)), array_agg(a.user || ':' || a.timestamp::date) FROM osmhistorynepal_feature a WHERE a.feature_type='node' GROUP BY a.feature_id, a.feature_type ) TO '/var/www/html/NepalOSMHistory/data/sampledaily/nodes.csv' WITH CSV DELIMITER ','"
# done
