#!/bin/bash
## create_tables.sh
## Create tables for specified boards.
##
set -v # Print lines as they are run (bash option).
echo "#[${0##*/}]" "Starting" "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
echo "#[${0##*/}]" "Running as: $(whoami)@$(hostname) in $(pwd)"


##=====< Config >=====##
mariadb_db="fourchan" # Database name.
mariadb_conf="root.my.cnf" # Superuser .my.cnf file.
boards=( # Shortnames of boards (e.g. 'mlp' or 'g' )
	'h'
	'i'
)
##=====< /Config >=====##


##=====< Create tables >=====##
echo "#[${0##*/}]" "boards=$boards"
mkdir -vp tmp/
for board in ${boards[@]}; do
    echo "#[${0##*/}]" "Creating tables for:" "board=$board"  "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"

    ## Template SQL:
    cp -v "create_tables.template.sql" tmp/"create_tables.${board}.sql"
    sed -i "s/%%BOARD%%/${board}/g" tmp/"create_tables.${board}.sql"

    ## Run the SQL:
    ## https://mariadb.com/kb/en/mysql-command-line-client/
   /bin/time/ -- mysql --defaults-extra-file="${mariadb_conf}" --database="${mariadb_db}" --progress-reports \
   		< tmp/"create_tables.${board}.sql"

    echo "#[${0##*/}]" "Created tables for:" "board=$board" "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
done
##=====< /Create tables >=====##


echo "#[${0##*/}]" "Finished" "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
