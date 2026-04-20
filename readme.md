# neofuuka-scraper

**neofuuka-scraper** is a next-generation 4chan scraper, written in Python.


Its primary goals are:
* Efficiency
* Accuracy of scraped data
* Reliability and error resilience

It currently supports the [Asagi](https://github.com/eksopl/asagi)+[FoolFuuka](https://github.com/FoolCode/FoolFuuka) MySQL schema and functions as a drop-in replacement for Asagi.  
In the future, more schemas may be supported.

## Vs. Asagi

All of Asagi's primary features are supported, with several fixes and improvements, including:

* **Significantly reduced database writes**: Every time a thread is modified, Asagi will run an insert+update query for every single post in it, including ones that have not changed. This scraper keeps track of post changes by storing a small hash in memory, and will only update posts that have actually changed.
* **Significantly reduced I/O when saving files**: Every time a thread is modified, Asagi will check for the existence of every single image in the thread, and will update the modification time of all full image files. This scraper only checks for each image once the first time a post is seen, and only updates modification times if configured to do so.
* **Higher data accuracy**: Asagi has some minor issues that result in saved data being slightly different than what it originally was, such as every `</span>` tag being replaced with `[/spoiler]`, recently created threads not being properly marked as deleted, etc. All such known issues are not present in this scraper.
* **Better overall performance and efficiency**: Asagi uses significantly more CPU/RAM/etc resources than it needs, mostly as a result of being written in Java. This scraper is significantly more efficient in many aspects.
* **Reduced request counts**: With the introduction of Catalog Scraping, it is possible to scrape boards with significantly less json data requests than Asagi. Read more about Catalog Scraping below.

However, unlike Asagi, this scraper **does not create database tables and triggers if they do not already exist**.  
Read the **Database Setup** section below for more info.

## Catalog Scraping

A new experimental method of scraping is supported: **Catalog Scraping**.  
On faster boards and with adequate configuration values, it can reduce request rates by **50% or more**.

When enabled with `catalogScrapeEnable`, the scraper will use `catalog.json` as the thread index instead of `threads.json`. For most boards, 4chan provides the last 5 replies of each thread in the catalog - the scaper will attempt to use this data to scrape posts for more active threads, instead of having to fetch the entire thread on every update.

When a thread is updated, the following conditions are checked:

* Less than `catalogScrapeTimeFreq` seconds have passed since the last update
* The newest reply seen in the previous update is present in the catalog data
* The reply count shown on the catalog matches the expected reply count

If all conditions are met, full thread fetching will be skipped and the catalog data will be used instead.  
At most, `catalogScrapeTimeWait` seconds may pass after the first catalog scrape before the full thread is forcefully fetched.

## Usage

Initial setup is simple:

* Download the repo
* Copy `scraper.ex.json` to `scraper.json`
* Make changes to `scraper.json` (see configuration info below)
* Ensure Python 3.7 or newer is installed
* Install required python modules with `python3 -m pip install -r requirements.txt`
* Ensure all the necessary database tables & triggers are set up (see below)
* Run the scraper with `python3 scraper.py`

After initial setup, it is recommended to run the scraper as a service (using something like systemd) to make it easier to manage and ensure it runs on startup and is restarted automatically if something goes wrong.

<details>
<summary>Example systemd service</summary>

```
[Unit]
Description=4chan Scraper
After=network-online.target mysql.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 -u scraper.py
WorkingDirectory=/home/example/scraper
User=example
Restart=always
RestartSec=180
Environment=
StandardOutput=null
StandardError=journal
SyslogIdentifier=scraper

[Install]
WantedBy=multi-user.target

```

</details>


## Configuration

The default configuration file is `./scraper.json`. You can change this with `--cfg <filename>`.

It should look like this:

```json
{
  "scraper": {
    "global": {
      "sourceBoard": null,
      "sourceFormat": "yotsuba",
      "timeBetweenIndexUpdates": 60,
      "etc": "..."
    },
    
    "boards": {
      "a": {
        "timeBetweenIndexUpdates": 30
      },
      
      "b": {
        "timeBetweenIndexUpdates": 20
      }
    }
  }
}
```

Values in the `global` section are the defaults for all boards.  
In the `boards` section, each board must be defined as an object, and any values inside will override the defaults for that board.  
The object key defines the board's name in the database. You may use `sourceBoard` to scrape from a board different than this name.

### List of configuration values

* `typeInput` - The type of source to scrape from. Only `yotsuba.json` is supported for now. *Value is not actually checked.*
* `typeOutput` - The type of data format to output to. Only `asagi` is supported for now. *Value is not actually checked.*
* `sourceBoard` - Board's name on 4chan. You can use this to scrape a board into a table with a different name.
* `sourceLinkPosts` - Base URL for text data (json).
* `sourceLinkFilesThb` - Base URL for thumbnail media files.
* `sourceLinkFilesSrc` - Base URL for original media files.
* `dbSrvHost` - Database server host.
* `dbSrvPort` - Database server port.
* `dbUserName` - Database username.
* `dbUserPass` - Database password.
* `dbDatabase` - Database name.
* `dbCharset` - Database connection charset. Always use `utf8mb4`.
* `doSavePosts` - Enable saving post text data to database. Don't disable this. This probably shouldn't even be an option.
* `doSaveFilesThb` - Enable saving thumbnail media files.
* `doSaveFilesSrc` - Enable saving original media files.
* `threadsForPosts` - How many threads to use to download post text data (json). Usually no more than `1` or `2` are needed.
* `threadsForFilesThb` - How many threads to use to download thumbnail media files. Suggested values are between `5` and `20`.
* `threadsForFilesSrc` - How many threads to use to download original media files. Suggested values are between `2` and `5`.
* `catalogScrapeEnable` - Enable use of catalog data to scrape posts. Reduces request counts significantly for faster boards. More info above in the Catalog Scraping section.
* `catalogScrapeTimeFreq` - How often a thread must be updating to be eligible for catalog scraping, in seconds. Suggested values are between `60` and `240`.
* `catalogScrapeTimeWait` - How long to wait before doing a full scrape on a thread that was catalog scraped, in seconds. Suggested values are between `240` and `600`. Higher values will result in lower poster count accuracy.
* `timeBetweenIndexUpdates` - How often to update the list of threads, in seconds. A good value for most boards is `60`. If catalog scraping on a fast board, lower values are more efficient.
* `timeBetweenTopicForceUpdates` - Threads will be updated at least this often, in seconds, even if they are not known to have been modified. Avoid setting this lower than `3600` (1h).
* `timeBetweenFileSaveAttempts` - If a file fails to download, how long before another download attempt happens, in seconds. *Unused, the scraper figures out an appropriate time by itself.*
* `indexArchiveOnStartup` - Scrape archived threads when the scraper starts up. *Archive scraping is untested and may not work properly.*
* `indexArchiveOnConnect` - Scrape archived threads when the scraper detects a connection issue (index fails to load several times in a row). *Archive scraping is untested and may not work properly.*
* `topicDeleteThreshold` - What page a thread must be on before it is considered naturally pruned if it disappears. Suggested values are `8` or `9` for 10-page boards. Only applies if the board doesn't have an internal archive.
* `fileSavePath` - Path on disk to save media files to. Currently uses the asagi file structure.
* `fileMaxPostAge` - Maximum post age, in seconds, to save media files for. Useful if you offload old media out of `fileSavePath` and don't want it to be redownloaded on slow boards when the scraper is restarted.
* `fileTouchOnDupe` - Touch original media files to update their modification time when a duplicate is encountered. Thumbnails are never touched.
* `fileMismatchRedo` - If a file is about to be downloaded but already exists, but the existing file doesn't match what's expected, delete and redownload. Untested, may have issues.
* `fileUseShortNames` - Use the old short (13 digit) timestamp filename format, from before 4chan added 3 extra digits to its filenames. Useful if you have an old database and have not yet increased the media name column size. Longer timestamps are truncated, but the original is saved in the `exif` column.
* `fileDupeCheckLink` - Base URL to send HEAD requests to before downloading original image files, to check if they already exist. *Not yet implemented.*
* `requestUserAgent` - User agent used for all requests.
* `requestTimeoutText` - Request timeout for text requests. Suggested values are between `20` and `60`.
* `requestTimeoutFile` - Request timeout for image requests. Suggested values are between `40` and `120`.
* `requestThrottleBoard` - Minimum time between requests for each board, in seconds. Suggested values are between `0.3` and `1.0`. Don't go too high on fast boards.
* `requestThrottleGlobal` - Minimum time between requests for all boards, in seconds. Be careful with this. If you have more than a few boards, just set it to zero.
* `blacklistPostFilter` - A board level config that's a regex pattern. If specified, will **never** download threads with matching subjects or comments.
* `whitelistPostFilter` - A board level config that's a regex pattern. If specified, will **only** download threads with matching subjects or comments. If `blacklistPostFilter` is specified and has a match, a thread will not be downloaded despite a `whitelistPostFilter` match.

## Database Setup

This scraper does not create database tables and triggers automatically if they do not already exist.  
You must create them manually using the code below before scraping a new board.

This SQL code includes important indexes usually missing from Asagi, and uses new high-performance triggers that allow for much faster inserts than the originals. These triggers do not support stats. All of this is backwards-compatible with Asagi and may be used with it.

Replace ``%%BOARD%%`` with the board name. If you use a database engine other than InnoDB, replace that as well.

<details>
<summary>SQL Code for Tables</summary>

```sql
CREATE TABLE `%%BOARD%%` (
	`doc_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
	`media_id` int(10) unsigned NOT NULL DEFAULT 0,
	`poster_ip` decimal(39,0) unsigned NOT NULL DEFAULT 0,
	`num` int(10) unsigned NOT NULL,
	`subnum` int(10) unsigned NOT NULL,
	`thread_num` int(10) unsigned NOT NULL DEFAULT 0,
	`op` tinyint(1) NOT NULL DEFAULT 0,
	`timestamp` int(10) unsigned NOT NULL,
	`timestamp_expired` int(10) unsigned NOT NULL,
	`preview_orig` varchar(50) DEFAULT NULL,
	`preview_w` smallint(5) unsigned NOT NULL DEFAULT 0,
	`preview_h` smallint(5) unsigned NOT NULL DEFAULT 0,
	`media_filename` text DEFAULT NULL,
	`media_w` smallint(5) unsigned NOT NULL DEFAULT 0,
	`media_h` smallint(5) unsigned NOT NULL DEFAULT 0,
	`media_size` int(10) unsigned NOT NULL DEFAULT 0,
	`media_hash` varchar(25) DEFAULT NULL,
	`media_orig` varchar(50) DEFAULT NULL,
	`spoiler` tinyint(1) NOT NULL DEFAULT 0,
	`deleted` tinyint(1) NOT NULL DEFAULT 0,
	`capcode` varchar(1) NOT NULL DEFAULT 'N',
	`email` varchar(100) DEFAULT NULL,
	`name` varchar(100) DEFAULT NULL,
	`trip` varchar(25) DEFAULT NULL,
	`title` varchar(100) DEFAULT NULL,
	`comment` text DEFAULT NULL,
	`delpass` tinytext DEFAULT NULL,
	`sticky` tinyint(1) NOT NULL DEFAULT 0,
	`locked` tinyint(1) NOT NULL DEFAULT 0,
	`poster_hash` varchar(8) DEFAULT NULL,
	`poster_country` varchar(2) DEFAULT NULL,
	`exif` text DEFAULT NULL,
	PRIMARY KEY (`doc_id`),
	UNIQUE KEY `num_subnum_index` (`num`,`subnum`),
	KEY `thread_num_subnum_index` (`thread_num`,`num`,`subnum`),
	KEY `subnum_index` (`subnum`),
	KEY `op_index` (`op`),
	KEY `media_id_index` (`media_id`),
	KEY `media_hash_index` (`media_hash`),
	KEY `media_orig_index` (`media_orig`),
	KEY `name_trip_index` (`name`,`trip`),
	KEY `trip_index` (`trip`),
	KEY `email_index` (`email`),
	KEY `poster_ip_index` (`poster_ip`),
	KEY `timestamp_index` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `%%BOARD%%_deleted` (
	`doc_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
	`media_id` int(10) unsigned NOT NULL DEFAULT 0,
	`poster_ip` decimal(39,0) unsigned NOT NULL DEFAULT 0,
	`num` int(10) unsigned NOT NULL,
	`subnum` int(10) unsigned NOT NULL,
	`thread_num` int(10) unsigned NOT NULL DEFAULT 0,
	`op` tinyint(1) NOT NULL DEFAULT 0,
	`timestamp` int(10) unsigned NOT NULL,
	`timestamp_expired` int(10) unsigned NOT NULL,
	`preview_orig` varchar(50) DEFAULT NULL,
	`preview_w` smallint(5) unsigned NOT NULL DEFAULT 0,
	`preview_h` smallint(5) unsigned NOT NULL DEFAULT 0,
	`media_filename` text DEFAULT NULL,
	`media_w` smallint(5) unsigned NOT NULL DEFAULT 0,
	`media_h` smallint(5) unsigned NOT NULL DEFAULT 0,
	`media_size` int(10) unsigned NOT NULL DEFAULT 0,
	`media_hash` varchar(25) DEFAULT NULL,
	`media_orig` varchar(50) DEFAULT NULL,
	`spoiler` tinyint(1) NOT NULL DEFAULT 0,
	`deleted` tinyint(1) NOT NULL DEFAULT 0,
	`capcode` varchar(1) NOT NULL DEFAULT 'N',
	`email` varchar(100) DEFAULT NULL,
	`name` varchar(100) DEFAULT NULL,
	`trip` varchar(25) DEFAULT NULL,
	`title` varchar(100) DEFAULT NULL,
	`comment` text DEFAULT NULL,
	`delpass` tinytext DEFAULT NULL,
	`sticky` tinyint(1) NOT NULL DEFAULT 0,
	`locked` tinyint(1) NOT NULL DEFAULT 0,
	`poster_hash` varchar(8) DEFAULT NULL,
	`poster_country` varchar(2) DEFAULT NULL,
	`exif` text DEFAULT NULL,
	PRIMARY KEY (`doc_id`),
	UNIQUE KEY `num_subnum_index` (`num`,`subnum`),
	KEY `thread_num_subnum_index` (`thread_num`,`num`,`subnum`),
	KEY `subnum_index` (`subnum`),
	KEY `op_index` (`op`),
	KEY `media_id_index` (`media_id`),
	KEY `media_hash_index` (`media_hash`),
	KEY `media_orig_index` (`media_orig`),
	KEY `name_trip_index` (`name`,`trip`),
	KEY `trip_index` (`trip`),
	KEY `email_index` (`email`),
	KEY `poster_ip_index` (`poster_ip`),
	KEY `timestamp_index` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `%%BOARD%%_images` (
  `media_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `media_hash` varchar(25) NOT NULL,
  `media` varchar(50) DEFAULT NULL,
  `preview_op` varchar(50) DEFAULT NULL,
  `preview_reply` varchar(50) DEFAULT NULL,
  `total` int(10) unsigned NOT NULL DEFAULT 0,
  `banned` smallint(5) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`media_id`),
  UNIQUE KEY `media_hash_index` (`media_hash`),
  KEY `total_index` (`total`),
  KEY `banned_index` (`banned`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `%%BOARD%%_threads` (
	`thread_num` int(10) unsigned NOT NULL,
	`time_op` int(10) unsigned NOT NULL,
	`time_last` int(10) unsigned NOT NULL,
	`time_bump` int(10) unsigned NOT NULL,
	`time_ghost` int(10) unsigned DEFAULT NULL,
	`time_ghost_bump` int(10) unsigned DEFAULT NULL,
	`time_last_modified` int(10) unsigned NOT NULL,
	`nreplies` int(10) unsigned NOT NULL DEFAULT 0,
	`nimages` int(10) unsigned NOT NULL DEFAULT 0,
	`sticky` tinyint(1) NOT NULL DEFAULT 0,
	`locked` tinyint(1) NOT NULL DEFAULT 0,
	PRIMARY KEY (`thread_num`),
	KEY `time_op_index` (`time_op`),
	KEY `time_bump_index` (`time_bump`),
	KEY `time_ghost_bump_index` (`time_ghost_bump`),
	KEY `time_last_modified_index` (`time_last_modified`),
	KEY `sticky_index` (`sticky`),
	KEY `locked_index` (`locked`),
	KEY `sticky_time_bump_index` (`sticky`,`time_bump`),
	KEY `sticky_time_ghost_bump_index` (`sticky`,`time_ghost_bump`),
	KEY `sticky_thread_num_index` (`sticky`,`thread_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

</details>

<details>
<summary>SQL Code for Triggers</summary>

```sql
DELIMITER \\

DROP PROCEDURE IF EXISTS `update_thread_%%BOARD%%`\\
DROP PROCEDURE IF EXISTS `create_thread_%%BOARD%%`\\
DROP PROCEDURE IF EXISTS `delete_thread_%%BOARD%%`\\
DROP PROCEDURE IF EXISTS `insert_image_%%BOARD%%`\\
DROP PROCEDURE IF EXISTS `delete_image_%%BOARD%%`\\
DROP PROCEDURE IF EXISTS `insert_post_%%BOARD%%`\\
DROP PROCEDURE IF EXISTS `delete_post_%%BOARD%%`\\

DROP TRIGGER IF EXISTS `before_ins_%%BOARD%%`\\
DROP TRIGGER IF EXISTS `after_ins_%%BOARD%%`\\
DROP TRIGGER IF EXISTS `after_del_%%BOARD%%`\\

CREATE PROCEDURE `update_thread_%%BOARD%%` (ins INT, tnum INT, subnum INT, timestamp INT, media INT, email VARCHAR(100))
BEGIN
  UPDATE
    `%%BOARD%%_threads` op
  SET
    op.time_last = IF((ins AND subnum = 0), GREATEST(timestamp, op.time_last), op.time_last),
    op.time_bump = IF((ins AND subnum = 0), GREATEST(timestamp, op.time_bump), op.time_bump),
    op.time_ghost = IF((ins AND subnum != 0), GREATEST(timestamp, COALESCE(op.time_ghost, 0)), op.time_ghost),
    op.time_ghost_bump = IF((ins AND subnum != 0 AND (email IS NULL OR email != 'sage')), GREATEST(timestamp, COALESCE(op.time_ghost_bump, 0)), op.time_ghost_bump),
    op.time_last_modified = GREATEST(timestamp, op.time_last_modified),
    op.nreplies = IF(ins, (op.nreplies + 1), (op.nreplies - 1)),
    op.nimages = IF(media, IF(ins, (op.nimages + 1), (op.nimages - 1)), op.nimages)
  WHERE op.thread_num = tnum;
END\\

CREATE PROCEDURE `create_thread_%%BOARD%%` (num INT, timestamp INT)
BEGIN
  INSERT IGNORE INTO `%%BOARD%%_threads` VALUES (num, timestamp, timestamp, timestamp, NULL, NULL, timestamp, 0, 0, 0, 0);
END\\

CREATE PROCEDURE `delete_thread_%%BOARD%%` (tnum INT)
BEGIN
  DELETE FROM `%%BOARD%%_threads` WHERE thread_num = tnum;
END\\

CREATE PROCEDURE `insert_image_%%BOARD%%` (n_media_hash VARCHAR(25), n_media VARCHAR(50), n_preview VARCHAR(50), n_op INT)
BEGIN
  IF n_op = 1 THEN
    INSERT INTO `%%BOARD%%_images` (media_hash, media, preview_op, total)
    VALUES (n_media_hash, n_media, n_preview, 1)
    ON DUPLICATE KEY UPDATE
      media_id = LAST_INSERT_ID(media_id),
      total = (total + 1),
      preview_op = COALESCE(preview_op, VALUES(preview_op)),
      media = COALESCE(media, VALUES(media));
  ELSE
    INSERT INTO `%%BOARD%%_images` (media_hash, media, preview_reply, total)
    VALUES (n_media_hash, n_media, n_preview, 1)
    ON DUPLICATE KEY UPDATE
      media_id = LAST_INSERT_ID(media_id),
      total = (total + 1),
      preview_reply = COALESCE(preview_reply, VALUES(preview_reply)),
      media = COALESCE(media, VALUES(media));
  END IF;
END\\

CREATE PROCEDURE `delete_image_%%BOARD%%` (n_media_id INT)
BEGIN
  UPDATE `%%BOARD%%_images` SET total = (total - 1) WHERE media_id = n_media_id;
END\\

CREATE TRIGGER `before_ins_%%BOARD%%` BEFORE INSERT ON `%%BOARD%%`
FOR EACH ROW
BEGIN
  IF NEW.media_hash IS NOT NULL THEN
    CALL insert_image_%%BOARD%%(NEW.media_hash, NEW.media_orig, NEW.preview_orig, NEW.op);
    SET NEW.media_id = LAST_INSERT_ID();
  END IF;
END\\

CREATE TRIGGER `after_ins_%%BOARD%%` AFTER INSERT ON `%%BOARD%%`
FOR EACH ROW
BEGIN
  IF NEW.op = 1 THEN
    CALL create_thread_%%BOARD%%(NEW.num, NEW.timestamp);
  END IF;
  CALL update_thread_%%BOARD%%(1, NEW.thread_num, NEW.subnum, NEW.timestamp, NEW.media_id, NEW.email);
END\\

CREATE TRIGGER `after_del_%%BOARD%%` AFTER DELETE ON `%%BOARD%%`
FOR EACH ROW
BEGIN
  CALL update_thread_%%BOARD%%(0, OLD.thread_num, OLD.subnum, OLD.timestamp, OLD.media_id, OLD.email);
  IF OLD.op = 1 THEN
    CALL delete_thread_%%BOARD%%(OLD.num);
  END IF;
  IF OLD.media_hash IS NOT NULL THEN
    CALL delete_image_%%BOARD%%(OLD.media_id);
  END IF;
END\\

DELIMITER ;
```

</details>

## Known Issues

* Saving some less important board-specific post metadata (such as exif and oekaki) is not yet supported, the data is silently dropped. Use asagi to scrape boards with this data.
