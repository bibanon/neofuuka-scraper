import json
import base64
import pymysql

from .ItemFile import *
from .Thread import *
from .Utils import *

class Inserter(Thread):
	def run(self):
		super().run()
		
		query_insert = \
			"INSERT INTO `{0}`" \
			" (num, subnum, thread_num, op, timestamp, timestamp_expired, preview_orig, preview_w," \
			" preview_h, media_filename, media_w, media_h, media_size, media_hash, media_orig, spoiler," \
			" deleted, capcode, name, trip, title, comment, sticky, locked, poster_hash, poster_country, exif)" \
			" SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s FROM DUAL" \
			" WHERE NOT EXISTS (SELECT 1 FROM `{0}` FORCE INDEX (num_subnum_index) WHERE num = %s AND subnum = 0)" \
			" AND NOT EXISTS (SELECT 1 FROM `{0}_deleted` FORCE INDEX (num_subnum_index) WHERE num = %s AND subnum = 0)"
		
		query_update = \
			"UPDATE `{0}` FORCE INDEX (num_subnum_index)" \
			" SET title = %s, comment = %s, spoiler = %s," \
			" sticky = (%s OR sticky), locked = (%s OR locked)," \
			" deleted = 0, timestamp_expired = 0," \
			" exif = COALESCE(%s, exif)" \
			" WHERE num = %s AND subnum = 0"
		
		query_delete = \
			"UPDATE `{0}` FORCE INDEX (num_subnum_index)" \
			" SET deleted = %s, timestamp_expired = %s" \
			" WHERE num = %s AND subnum = 0"
		
		query_insert = query_insert.format(self.board.get_name())
		query_update = query_update.format(self.board.get_name())
		query_delete = query_delete.format(self.board.get_name())
		
		while True:
			if self.board.stop(): break
			
			posts = []
			
			# grab a set of posts to insert
			
			with self.board.lock:
				for post in self.board.save_posts:
					posts.append(post)
					
					# limit post batch size
					if len(posts) >= 300: break
					
					continue
				
				for post in posts:
					self.board.save_posts.remove(post)
			
			values_insert = []
			values_update = []
			values_delete = []
			
			# prepare insert/update query values
			# TODO: maybe keep track of already inserted posts and skip insert
			
			with self.board.lock:
				for post in posts:
					comment = post.comment
					comment = (comment if comment else None)
					comment = (asagi_comment_parse(comment) if comment else comment)
					comment = (comment[0:16384] if comment else comment) # mysql text limits bytes not chars
					
					extra = post.get_extra()
					extra = (json_encode_obj(extra) if extra else extra)
					
					values_insert.append([
						(post.number),
						(0),
						(post.topic.number),
						(1 if post.is_opener() else 0),
						(asagi_timestamp_conv(post.time_posted)),
						(0),
						(f"{post.file_time_s}s.jpg" if post.file_time else None),
						(post.file_dims_thb[0] if post.file_time else 0),
						(post.file_dims_thb[1] if post.file_time else 0),
						(asagi_html_escape(f"{post.file_name}.{post.file_type}") if post.file_time else None),
						(post.file_dims_src[0] if post.file_time else 0),
						(post.file_dims_src[1] if post.file_time else 0),
						(post.file_size if post.file_time else 0),
						(post.get_file_hash_b64() if post.file_time else None),
						(f"{post.file_time_s}.{post.file_type}" if post.file_time else None),
						(1 if post.spoiler else 0),
						(0),
						(asagi_capcode_conv(post.poster_capcode)),
						(post.poster_name[0:100] if post.poster_name else None),
						(post.poster_trip[0:25] if post.poster_trip else None),
						(post.subject[0:100] if post.subject else None),
						(comment if comment else None),
						(1 if post.is_opener() and post.topic.sticky else 0),
						(1 if post.is_opener() and post.topic.closed else 0),
						(post.poster_userid[0:8] if post.poster_userid else None),
						(post.poster_country[0:2] if post.poster_country else None),
						(extra),
						(post.number),
						(post.number),
					])
					
					values_update.append([
						(post.subject[0:100] if post.subject else None),
						(comment if comment else None),
						(1 if post.spoiler else 0),
						(1 if post.is_opener() and post.topic.sticky else 0),
						(1 if post.is_opener() and post.topic.closed else 0),
						(extra if not post.topic.time_archived else None),
						(post.number),
					])
			
			# prepare delete query values
			
			removals_topic = None
			removals_post = None
			
			with self.board.lock:
				removals_topic = []
				
				for topic in self.board.topics:
					if topic.posts_ins:
						removals_post = []
						
						for post in topic.posts.values():
							if post.insert:
								skip = False
								
								for post1 in self.board.save_posts:
									if post.number == post1.number:
										# post is waiting to be inserted
										skip = True
										break
								
								if skip:
									continue
								
								post.insert = False
								
								values_delete.append([
									(1 if post.time_deleted_post else 0),
									(asagi_timestamp_conv(post.time_deleted_post) if post.time_deleted_post else 0),
									(post.number)
								])
								
								if (
									post.time_deleted_post and
									post.number != topic.number
								):
									# remove deleted posts from topic
									
									# occasionally there can be an inconsistency where a post disappears and reappears?
									# if this happens the post will be re-added and un-deleted, so nothing goes wrong
									
									removals_post.append(post)
						
						for item in removals_post:
							topic.posts.pop(item.number, None)
						
						topic.update_posts_ins()
					
					if (
						topic.time_deleted or
						topic.time_archived
					):
						# remove dead topics
						removals_topic.append(topic)
					
					if topic.time_archived:
						try:
							if self.board.storage.conn:
								self.board.storage.conn.set(
									name=self.board.storage.key(["board", self.board.get_name(), "topic", topic.number, "archived"]),
									value="1",
									ex=(60*60*24*20),
								)
						except:
							pass
				
				for item in removals_topic:
					self.board.topics.remove(item)
			
			if (
				len(values_insert) == 0 and
				len(values_update) == 0 and
				len(values_delete) == 0
			):
				# nothing to do right now
				self.board.sleep(1.0)
				continue
			
			# self.board.log(self, f"Inserting a batch of {len(posts)} posts")
			
			# TODO: simply looping infinitely might not be the best idea
			# or maybe it is, inserts should never fail on specific posts
			# if they do fail, something's wrong and it should be evident
			
			while True:
				if self.board.stop(): break
				
				try:
					self.board.database.act_start()
					
					# run insert/update queries
					
					cursor = self.board.database.cursor()
					
					cursor.executemany(query_insert, values_insert)
					cursor.executemany(query_update, values_update)
					cursor.executemany(query_delete, values_delete)
					
					self.board.database.commit()
					
					cursor.close()
					
					# process files after insert
					# using batched IN query
					
					hashes = []
					
					for post in posts:
						if post.file_time:
							hashes.append(post.get_file_hash_b64())
					
					if len(hashes):
						cursor = self.board.database.cursor()
						
						query = "SELECT * FROM `{}_images` FORCE INDEX (media_hash_index) WHERE media_hash IN ({})"
						query = query.format(self.board.get_name(), ",".join(["%s"] * len(hashes)))
						
						cursor.execute(query, hashes)
						
						rows = {}
						
						for row in cursor.fetchall():
							rows[row["media_hash"]] = row
						
						cursor.close()
						
						with self.board.lock:
							for post in posts:
								if post.file_time:
									row = rows.get(post.get_file_hash_b64())
									
									if (
										row and
										int(row["banned"]) == 0
									):
										for type in FileType1:
											# check if we're configured to save this type
											if type == FileType1.THB and not self.board.conf.get("doSaveFilesThb"): continue
											if type == FileType1.SRC and not self.board.conf.get("doSaveFilesSrc"): continue
											
											file = ItemFile(post, type)
											
											try:
												if type == FileType1.THB:
													name = ("op" if post.is_opener() else "reply")
													name = row["preview_" + name]
													name = name.split("s.")[0]
												else:
													name = row["media"]
													name = name.split(".")[0]
												
												# set asagi target name
												file.time1 = int(name)
												
												self.board.save_files.append(file)
											except:
												pass
					
					self.board.database.act_finish()
					
					break
				except Exception as err:
					self.board.database.error(err)
					pass
				
				self.board.sleep(1.0)
				continue
			
			if len(posts) > 100:
				self.board.sleep(0.1)
			else:
				self.board.sleep(0.5)
			
			continue
