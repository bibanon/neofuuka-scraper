#!/bin/bash
## create-triggers.sh
## Create triggers for specified boards.
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


##=====< Create triggers >=====##
echo "#[${0##*/}]" "boards=$boards"
mkdir -vp tmp/
for board in ${boards[@]}; do
    echo "#[${0##*/}]" "Creating triggers for:" "board=$board"  "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"

    ## Template SQL:
    cp -v "create_triggers.template.sql" tmp/"create_triggers.${board}.sql"
    sed -i "s/%%BOARD%%/${board}/g" tmp/"create_triggers.${board}.sql"

    ## Run the SQL:
    ## https://mariadb.com/kb/en/mysql-command-line-client/
   /bin/time/ -- mysql --defaults-extra-file="${mariadb_conf}" --database="${mariadb_db}" --progress-reports \
   		< tmp/"create_triggers.${board}.sql"

    echo "#[${0##*/}]" "Created triggers for:" "board=$board" "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
done
##=====< /Create triggers >=====##


echo "#[${0##*/}]" "Finished" "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
