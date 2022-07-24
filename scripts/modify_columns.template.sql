/* modify_columns.template.sql
 * Modify tables for Neofuuka to be compatable with net 4chan image timestamp values.
 * (This change occured during 2022-07.)
 *
 * $ cp -v "modify_columns.template.sql" "modify_columns.${board}.sql"
 * $ sed -i "s/%%BOARD%%/${board}/g" "modify_columns.${board}.sql"
 * 
 * $ mysql --defaults-extra-file="${mariadb_conf}" --database="${mariadb_db}" \
 *    < "modify_columns.${board}.sql"
 */

 /* BOARD */
ALTER TABLE `%%BOARD%%` MODIFY `preview_orig` varchar(23) DEFAULT NULL ;
ALTER TABLE `%%BOARD%%` MODIFY `media_orig` varchar(23) DEFAULT NULL ;

/* BOARD_deleted */
ALTER TABLE `%%BOARD%%` MODIFY `preview_orig` varchar(23) DEFAULT NULL ;
ALTER TABLE `%%BOARD%%` MODIFY `media_orig` varchar(23) DEFAULT NULL ;

/* BOARD_images */
ALTER TABLE `%%BOARD%%_images` MODIFY `media` VARCHAR(23) DEFAULT NULL ;
ALTER TABLE `%%BOARD%%_images` MODIFY `preview_op` VARCHAR(23) DEFAULT NULL ;
ALTER TABLE `%%BOARD%%_images` MODIFY `preview_reply` VARCHAR(23) DEFAULT NULL ;

COMMIT ;
