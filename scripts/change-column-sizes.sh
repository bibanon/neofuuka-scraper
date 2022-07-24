#!/bin/bash
## change-column-sizes.sh
## Modify tables for Neofuuka to be compatable with net 4chan image timestamp values.
## (This change occured during 2022-07.)
##
set -v # Print lines as they are run (bash option).
echo "#[${0##*/}]" "Starting"
echo "#[${0##*/}]" "Running as: $(whoami)@$(hostname)"


##=====< Config >=====##
mariadb_db="fourchan" # Database name.
mariadb_conf="root.my.cnf" # Superuser .my.cnf file.
boards=( # Shortnames of boards (e.g. 'mlp' or 'g' )
	'g'
	'a'
	'c'
	'k'
)
##=====< /Config >=====##


##=====< Modify tables and triggers >=====##
echo "#[${0##*/}]" "boards=$boards"
mkdir -vp tmp/ # Just a place to temporarily store the SQL for templating and execution.
for board in ${boards[@]}; do
    echo "#[${0##*/}]" "Modifying columns and triggers for:" "board=$board"

    ## ----- < Modify columns > ----- ##
    ## ALTER TABLE statements have to be used here, so it needs its own SQL template file.
    echo "#[${0##*/}]" "Altering tables for:" "board=$board"  "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
    
    ## Template SQL:
    cp -v "modify_columns.template.sql" tmp/"modify_columns.${board}.sql"
    sed -i "s/%%BOARD%%/${board}/g" tmp/"modify_columns.${board}.sql"

    ## Run the SQL:
    ## https://mariadb.com/kb/en/mysql-command-line-client/
    /bin/time/ -- mysql --defaults-extra-file="${mariadb_conf}" --database="${mariadb_db}" \
   		< tmp/"modify_columns.${board}.sql"
        
    echo "#[${0##*/}]" "Altered tables for:" "board=$board"  "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
    ## ----- < /Modify columns > ----- ##


    ## ----- < /Modify triggers > ----- ##
    ## The create triggers SQL drops triggers and recreates them already, so just copypaste it (with the appropriate column sizes fixed).
    echo "#[${0##*/}]" "Creating triggers for:" "board=$board"  "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
    
    ## Template SQL:
    cp -v "create_triggers.template.sql" tmp/"create_triggers.${board}.sql"
    sed -i "s/%%BOARD%%/${board}/g" tmp/"create_triggers.${board}.sql"

    ## Run the SQL:
    ## https://mariadb.com/kb/en/mysql-command-line-client/
   /bin/time/ -- mysql --defaults-extra-file="${mariadb_conf}" --database="${mariadb_db}" --progress-reports \
   		< tmp/"create_triggers.${board}.sql"
        
    echo "#[${0##*/}]" "Created triggers for:" "board=$board" "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
    ## ----- < /Modify triggers > ----- ##

    echo "#[${0##*/}]" "Modified:" "board=$board"
done
##=====< /Modify tables and triggers >=====##


echo "#[${0##*/}]" "Finished" "[at $(date +%Y-%m-%d_%H-%M%z=@%s)]"
