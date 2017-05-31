# A dirty script to pull files from it's learning
# - Bart van Blokland

# USAGE:
# 0. Install Python 3.x (including pip) if you haven't already
# 1. Look in the imports section, and install any packages you don't already have (pip commands are listed)
# 2. Scroll down a few lines to the settings area, and find the variables for your username and password. Put your credentials there.
# 3. Run the script ('python scrape.py')

# WHAT IS DOWNLOADED BY THIS SCRIPT?
# 1. All messages, both through the new and old system, including attachments
# 2. Bulletin messages and text posts, including comments
# 3. Assignments. 
#	3.1: If you're a student, your submission
#	3.2: If you teach the course, all student submissions, grades, and feedback
# 4. Forum posts. Includes any attached images.
# 5. Notes and links (both old and new style)
# 6. Surveys and tests (if you have sufficient access, the It's Learning generated reports are also snagged along)
# 7. Files

# The same folder structure as the course is kept.
# There may still be things the script doesn't grab. But at least the most important parts are there.

# You may need to set It's Learning's language to English (might be an innsida setting, not sure).
# Some bits and pieces rely on the english language pack (sorry, there was no easy other way)



# --- IMPORTS ---

# Install with "pip install requests"
import requests
from requests.exceptions import InvalidURL
# Install with "pip install lxml"
from lxml.html import fromstring, tostring
from lxml import etree

# Python std lib imports
import os.path
import os
import re
import html
import sys
import platform
import json
import base64
from shutil import rmtree
from time import sleep
from urllib.parse import urlparse
# Requires Python 3.4
from pathlib import Path

# --- SETTINGS ---

# Enter your username and password here, just as you would use them to log into innsida.
# Note that the requests library is awesome and sends everything over HTTPS.
ntnu_user = ''
ntnu_pass = ''

# I've sprinkled delays around the code to ensure the script isn't spamming requests at maximum rate.
# Each time such a delay occurs, it waits for this many seconds.
# Feel free to increase this if you plan to run this script overnight.
rate_limiting_delay_seconds = 1

# Some bits and pieces of text may contain special characters. Since a number of these are used
# in file paths and file names, they have to be filtered out. 
# Filename characters are deleted from file names
# File path characters are only deleted from entire/complete file paths
# I may have missed one of two. 
invalid_path_characters = [':', ',', '*', '?', '"', '<', '>', '\t', '`', '´', '|']
invalid_filename_characters = [':', '.', ',', '*', '/', '\\', '?', '"', '<', '>', '\t', '`', '´', '|']

# All output files will receive this extension. Since a lot of stuff contains raw HTML, I used HTML
# as the file type. You may want to change this to .txt though, since many files also contain plaintext bits.
output_text_extension = '.html'

# Use if the program crashed and stopped early. Skips to a course with a specific index
# If this value is non-zero, also downloading of the messaging inbox will be skipped.
# The index is 1-indexed, and corresponds to the course index listed on the print messages in the console
# when the dumping of a new course is started.
skip_to_course_with_index = 0

# Determines where the program dumps its output. 
# Note that the tailing slash is mandatory. 
output_folder_name = 'dump/'

# If a crash occurs, the script can skip all elements in folders up to the point where it left off. 
# The state is stored in a small text file created inside the working directory.
# Turn this setting on to allow the creation of these checkpoints. They are only really useful if you can fix the issue causing the crash in the first place.
enable_checkpoints = False

# --- CONSTANTS ---

computer_vision = 'https://ntnu.itslearning.com/ContentArea/ContentArea.aspx?LocationID=64728&LocationType=1'
innsida = 'https://innsida.ntnu.no'
feide_base_url = 'https://idp.feide.no/simplesaml/module.php/feide/login.php'
itslearning_url = 'https://innsida.ntnu.no/sso?target=itslearning'
itsleaning_course_list = 'https://ntnu.itslearning.com/Course/AllCourses.aspx'
itslearning_course_base_url = 'https://ntnu.itslearning.com/ContentArea/ContentArea.aspx'
itslearning_bulletin_base_url = 'https://ntnu.itslearning.com/Course/course.aspx?CourseId='
itslearning_bulletin_next_url = 'https://ntnu.itslearning.com/Bulletins/Page?courseId={}&boundaryLightBulletinId={}&boundaryLightBulletinCreatedTicks={}'
itslearning_folder_base_url = 'https://ntnu.itslearning.com/Folder/processfolder.aspx?FolderID='
itslearning_file_base_url = 'https://ntnu.itslearning.com/File/fs_folderfile.aspx?FolderFileID='
itslearning_assignment_base_url = 'https://ntnu.itslearning.com/essay/read_essay.aspx?EssayID='
itslearning_note_base_url = 'https://ntnu.itslearning.com/note/View_Note.aspx?NoteID='
itslearning_discussion_base_url = 'https://ntnu.itslearning.com/discussion/list_discussions.aspx?DiscussionID='
itslearning_weblink_base_url = 'https://ntnu.itslearning.com/weblink/weblink.aspx?WebLinkID='
itslearning_weblink_header_base_url = 'https://ntnu.itslearning.com/weblink/weblink_header.aspx?WebLinkID=' 
itslearning_learning_tool_base_url = 'https://ntnu.itslearning.com/LearningToolElement/ViewLearningToolElement.aspx?LearningToolElementId='
itslearning_messaging_url = 'https://ntnu.itslearning.com/Messages/Messages.aspx'
itslearning_comment_service = 'https://ntnu.itslearning.com/Services/CommentService.asmx/GetOldComments?sourceId={}&sourceType={}&commentId={}&count={}&numberOfPreviouslyReadItemsToDisplay={}&usePersonNameFormatLastFirst={}'
itslearning_root_url = 'https://ntnu.itslearning.com'
itslearning_not_found = 'https://ntnu.itslearning.com/not_exist.aspx'
itslearning_test_base_url = 'https://ntnu.itslearning.com/test/view_survey_list.aspx?TestID='
old_messaging_api_url = 'https://ntnu.itslearning.com/Messages/InternalMessages.aspx?MessageFolderId={}'
itslearning_picture_url = 'https://ntnu.itslearning.com/picture/view_picture.aspx?PictureID={}&FolderID=-1&ChildID=-1&DashboardHierarchyID=-1&DashboardName=&ReturnUrl='
innsida_login_parameters = {'SessionExpired': 0}
progress_file_location = os.path.join(os.getcwd(), 'saved_progress_state.txt')

overflow_count = 0

# --- HELPER FUNCTIONS ---

def delay():
	sleep(rate_limiting_delay_seconds)

def convert_html_content(html_string):
	unescaped = html.unescape(html_string).split('\n')
	return '\n'.join([string.strip() for string in unescaped])

def sanitisePath(filePath):
	# I don't care about efficiency.
	for character in invalid_path_characters:
		filePath = filePath.replace(character, '')
	filePath = '/'.join([m.strip() for m in filePath.split('/')])
	return filePath

def createUniqueFilename(path):
	path_exported = Path(path)
	folder_parts = path_exported.parts[0:-1]
	file_name = '.'.join(path_exported.name.split('.')[0:-1])
	extension = path_exported.name.split('.')[-1]
	count = 1
	while os.path.exists(path):
		path = '/'.join(folder_parts) + '/' + file_name + ' (Duplicate ' + str(count) + ').' + extension
		count += 1
	return path

def sanitiseFilename(filename):
	for character in invalid_filename_characters:
		filename = filename.replace(character, '')
	return filename

def makeDirectories(path):
	cleaned_path = sanitisePath(path)
	os.makedirs(os.path.abspath(cleaned_path))
	return cleaned_path

# Windows has this amazing feature called "255 character file path limit"
# Here's a function made specifically for countering this issue.
def dumpToOverflow(content, filename):
	global overflow_count
	overflow_count += 1
	basename = os.path.basename(sanitisePath(filename))
	overflowDirectory = output_folder_name + 'Overflowed Files'
	if not os.path.exists(overflowDirectory):
		overflowDirectory = makeDirectories(overflowDirectory)
	total_path = sanitisePath(overflowDirectory + '/' + str(overflow_count) + '_' + basename)
	with open(total_path, 'wb') as file:
		file.write(content)
	print('FILE WAS WRITTEN TO OVERFLOW DIRECTORY - path too long (Windows issue)')
	print('Original file path:', filename.encode('ascii', 'ignore'))
	print('New file path:', total_path.encode('ascii', 'ignore'))

def bytesToTextFile(content, filename):
	filename = sanitisePath(filename)
	filename = os.path.abspath(createUniqueFilename(filename))
	if len(filename) >= 254 and 'Windows' in platform.system():
		dumpToOverflow(content, filename)
	else:
		with open(filename, 'wb') as file:
			file.write(content)

# Conversion between formats of one library to another
def convert_lxml_form_to_requests(lxml_form_values):
	form_dict = {}
	for item in lxml_form_values.form_values():
		form_dict[item[0]] = item[1]
	return form_dict

def do_feide_relay(relay_response):
	relay_page = fromstring(relay_response.text)
	relay_form = relay_page.forms[0]

	relay_form_dict = convert_lxml_form_to_requests(relay_form)

	return session.post(relay_form.action, data = relay_form_dict)

def download_file(url, destination_directory, session, index=None, filename=None, disableFilenameReencode=False):
	try:
		file_download_response = session.get(url, allow_redirects=True)
	except Exception:
		# Can occur in a case of an encoded image. If so, dump it.
		if 'https://ntnu.itslearning.comdata:image/png;base64,' in url or 'https://ntnu.itslearning.comdata:image/jpeg;base64,' in url:
			extension = url.split(':')[2].split(';')[0].split('/')[1]
			print('\tDownloaded Base64 encoded {} image'.format(extension))
			start_index = url.index(',') + 1
			base64_encoded_file_contents = url[start_index:]
			decoded_bytes = base64.b64decode(base64_encoded_file_contents)
			bytesToTextFile(decoded_bytes, destination_directory + '/' + base64_encoded_file_contents[0:10] + '.' + extension)
		else:
			print('FAILED TO DOWNLOAD FILE (INVALID URL):', url.encode('ascii', 'ignore'))
		return
	
	# If links are not directed to it's learning, the header format might be different
	if filename is None:
		try:
			filename_header = file_download_response.headers['Content-Disposition']
			filename_start = filename_header.split('filename="')[1]
			filename_end = filename_start.find('"')
			filename = filename_start[0:filename_end]
		except (KeyError, IndexError):
			# Hope that the filename was part of the URL
			filename = os.path.basename(urlparse(url).path)

	if index is not None:
		filename = str(index) + '_' + filename

	# Fix shitty decoding done by requests
	if not disableFilenameReencode:
		initial_filename = filename
		try:
			filename = filename.encode('latin1').decode('utf-8')
		except UnicodeDecodeError:
			filename = initial_filename

	# Special case where the server puts slashes in the file name
	# sanitiseFilename() cuts away too many characters here.
	filename = filename.replace('/', '')
	
	print('\tDownloaded', filename.encode('ascii', 'ignore'))
	if not os.path.exists(destination_directory):
		destination_directory = makeDirectories(destination_directory)


	filename = sanitisePath(filename)
	total_file_name = os.path.abspath(sanitisePath(destination_directory) + "/" + filename)
	total_file_name = createUniqueFilename(total_file_name)
	if len(total_file_name) >= 255 and 'Windows' in platform.system():
		dumpToOverflow(file_download_response.content, total_file_name)
	else:
		with open(total_file_name, 'wb') as outputFile:
			outputFile.write(bytearray(file_download_response.content))

	# Add sleep for rate limiting
	delay()

def loadPaginationPage(page_url, current_page_document, backpatch_character_index = 6):
	next_page_button = current_page_document.find_class('previous-next')
	found_next_button = False
	for element in next_page_button:
		if len(element) > 0 and (element[0].get('title') == 'Next' or element[0].get('title') == 'Neste'):
			next_page_button = element
			found_next_button = True
			break

	if not found_next_button:
		print('\tItem complete: this was the last page')
		return False, None

	print('\tLoading next page')
	# Locating the event name for obtaining the next page
	post_back_event = next_page_button[0].get('id')
	
	# Backpatching event title
	post_back_event = list(post_back_event)
	post_back_event[backpatch_character_index] = '$'
	post_back_event = ''.join(post_back_event)
	#print('Pagination load debug info:')
	#print(etree.tostring(next_page_button))
	#print(post_back_event)
	#print(page_url)

	# Editing the necessary form field
	pagination_form = None
	for form in current_page_document.forms:
		if '__EVENTTARGET' in form.fields:
			pagination_form = form
			break

	if pagination_form is None:
		raise Error('No pagination form found on page!')

	pagination_form = current_page_document.forms[0]
	pagination_form.fields['__EVENTTARGET'] = post_back_event
	post_data = convert_lxml_form_to_requests(pagination_form)

	# Submitting the form to obtain the next page
	headers = {}
	headers['Referer'] = page_url

	messaging_response = session.post(page_url, headers=headers, data=post_data, allow_redirects=True)

	return True, messaging_response


# --- DUMPING OF VARIOUS BITS OF ITS LEARNING FUNCTIONALITY ---

def processTest(pathThusFar, testURL, session):
	test_response = session.get(testURL, allow_redirects = True)
	test_document = fromstring(test_response.text)
	
	test_title = test_document.find_class('ccl-pageheader')[0][0].text_content()
	print('\tDownloading test/survey:', test_title.encode('ascii', 'ignore'))

	dumpDirectory = pathThusFar + '/Test - ' + test_title
	dumpDirectory = sanitisePath(dumpDirectory)
	dumpDirectory = makeDirectories(dumpDirectory)

	manualDumpDirectory = dumpDirectory + '/Explicit dump'
	manualDumpDirectory = makeDirectories(manualDumpDirectory)

	try:
		# If we have access to downloading all results, we do so here.
		# Since 'we can, grabbing both XLS and HTML reports.'
		show_result_url = itslearning_root_url + test_document.get_element_by_id('result')[0].get('href')[2:]
		download_file(show_result_url + '&Type=2', dumpDirectory, session, disableFilenameReencode=False)
		download_file(show_result_url + '&Type=2&HtmlType=true', dumpDirectory, session, disableFilenameReencode=False)
		print('\tIt\'s Learning generated report downloaded.')
	except KeyError:
		# No problem that we can't see the 'show result button, the manual dump will catch whatever is visible to us'
		pass

	pages_remaining = True
	while pages_remaining:
		row_index = 1
		entries_remaining = True
		while entries_remaining:
			try:
				table_entry_element = test_document.get_element_by_id('row_{}'.format(row_index))
			except KeyError:
				# End the loop when there are no more submissions
				print('\tAll entries found on page.')
				entries_remaining = False
				continue

			index_offset = 0
			if len(table_entry_element[0]) > 0 and table_entry_element[0][0].get('id') is not None and 'check' in table_entry_element[0][0].get('id'):
				index_offset = 1

			entry_name = table_entry_element[0 + index_offset].text_content()
			entry_date = table_entry_element[1 + index_offset].text_content()
			entry_url = itslearning_root_url + table_entry_element[2 + index_offset][0].get('href')[2:]

			print('\tDownloading response from', entry_name.encode('ascii', 'ignore'))

			entry_response = session.get(entry_url, allow_redirects=True)
			entry_document = fromstring(entry_response.text)

			file_content = convert_html_content(etree.tostring(entry_document.find_class('itsl-formbox')[0]).decode('utf-8')).encode('utf-8')

			file_name = manualDumpDirectory + '/' + sanitiseFilename(entry_name) + ' ' + sanitiseFilename(entry_date) + output_text_extension

			bytesToTextFile(file_content, file_name)

			row_index += 1

			delay()

		# Searching for the next pagination button
		# Of course this page has its own mechanism for this
		next_page_button = test_document.find_class('previous-next')
		found_next_button = False
		for element in next_page_button:
			if len(element) > 0 and element[0].get('title') == 'Next':
				next_page_button = element
				found_next_button = True
				break

		if not found_next_button:
			print('\tNo more pages found. All items have been downloaded.')
			break

		next_page_url = html.unescape(next_page_button[0].get('href'))[2:]

		print('\tPage finished, moving on to next page.')
		test_response = session.get(itslearning_root_url + next_page_url, allow_redirects = True)
		test_document = fromstring(test_response.text)

def processNote(pathThusFar, noteURL, session):
	note_response = session.get(noteURL, allow_redirects=True)
	note_document = fromstring(note_response.text)

	note_title_node = note_document.find_class('ccl-pageheader')[0]
	note_title = sanitiseFilename(note_title_node[0].text_content())
	
	print("\tDownloaded note:", note_title.encode('ascii', 'ignore'))

	dumpDirectory = pathThusFar + '/Note - ' + note_title
	dumpDirectory = sanitisePath(dumpDirectory)
	dumpDirectory = makeDirectories(dumpDirectory)

	note_content_div = note_document.find_class('h-userinput')[0]

	for image_tag in note_content_div.iterfind(".//img"):
		image_URL = image_tag.get('src')
		download_file(image_URL, dumpDirectory, session)

	bytesToTextFile(etree.tostring(note_content_div), dumpDirectory + '/' + note_title + output_text_extension)

def processWeblink(pathThusFar, weblinkPageURL, link_title, session):
	print('\tDownloading weblink: ', link_title.encode('ascii', 'ignore'))

	weblink_response = session.get(weblinkPageURL, allow_redirects=True)
	weblink_document = fromstring(weblink_response.text)

	header_frame = weblink_document.find(".//frame")
	header_src = header_frame.get('src')

	weblink_header_response = session.get(itslearning_weblink_header_base_url + header_src.split('=')[1], allow_redirects=True)
	weblink_header_document = fromstring(weblink_header_response.text)

	link_info_node = weblink_header_document.find_class('frameheaderinfo')[0]
	try:
		weblink_url = etree.tostring(link_info_node[0][1], encoding='utf-8')
	except IndexError:
		# Some older versions have some comment/section/other cruft. It's hard to tell how to get the info out consistently, so let's try one way and hope for the best.
		weblink_url = etree.tostring(link_info_node.find_class('standardfontsize')[0][1], encoding='utf-8')

	link_title = sanitiseFilename(link_title)

	link_file_content = (link_title + '\n\n').encode('utf-8') + weblink_url

	bytesToTextFile(link_file_content, pathThusFar + '/Link - ' + link_title + output_text_extension)

def processLearningToolElement(pathThusFar, elementURL, session):
	element_response = session.get(elementURL, allow_redirects=True)
	element_document = fromstring(element_response.text)

	element_title = element_document.get_element_by_id('ctl00_PageHeader_TT').text
	element_title = sanitiseFilename(element_title)
	print('\tDownloaded Learning Tool Element: ', element_title.encode('ascii', 'ignore'))

	frameSrc = element_document.get_element_by_id('ctl00_ContentPlaceHolder_ExtensionIframe').get('src')

	frame_content_response = session.get(frameSrc, allow_redirects=True)
	bytesToTextFile(frame_content_response.content, pathThusFar + '/Learning Tool Element - ' + element_title + output_text_extension)

def processPicture(pathThusFar, pictureURL, session):
	picture_response = session.get(pictureURL, allow_redirects=True)
	picture_document = fromstring(picture_response.text)

	element_title = picture_document.find_class('ccl-pageheader')[0].text_content()
	element_title = sanitiseFilename(element_title)
	print('\tDownloaded Picture:', element_title.encode('ascii', 'ignore'))

	dumpDirectoryPath = pathThusFar + '/Picture - ' + element_title
	dumpDirectoryPath = makeDirectories(dumpDirectoryPath)

	image_base_element = picture_document.find_class('itsl-formbox')[0]
	imageURL = itslearning_root_url + image_base_element[0][0].get('src')
	download_file(imageURL, dumpDirectoryPath, session)

	description_text = etree.tostring(image_base_element[2], encoding='utf-8')
	bytesToTextFile(description_text, dumpDirectoryPath + "/caption" + output_text_extension)

def processDiscussionPost(pathThusFar, postURL, postTitle, session):
	print("\tDownloading thread:", postTitle.encode('ascii', 'ignore'))
	post_response = session.get(postURL, allow_redirects=True)
	post_document = fromstring(post_response.text)

	post_table_tag = post_document.find_class('threadViewTable')[0]
	post_table_root = post_table_tag
	if post_table_root[0].tag == 'tbody':
			post_table_root = post_table_root[0]

	postDumpDirectory = pathThusFar + '/Thread - ' + sanitiseFilename(postTitle)
	completeDumpFile = postDumpDirectory
	duplicateCount = 1
	while os.path.exists(completeDumpFile):
		if duplicateCount > 1:
			completeDumpFile = postDumpDirectory + ' (Duplicate '+str(duplicateCount)+')'
		else:
			completeDumpFile = postDumpDirectory + ' (Duplicate)'
		duplicateCount += 1
	completeDumpFile = sanitisePath(completeDumpFile)

	fileContents = ''
	tags_to_next_entry = 0

	for index, post_tag in enumerate(post_table_root):
		if tags_to_next_entry != 0:
			# Each post is 3 tags
			tags_to_next_entry -= 1
			continue
		
		tags_to_next_entry = 2

		fileContents += '-------------------------------------------------------------------------\n'

		post_contents_tag = post_tag.getnext()

		is_post_deleted = 'deleted' in post_contents_tag[0][0].get('class')

		if is_post_deleted:
			# Deleted posts do not have a third footer entry like regular posts do, so we move on the the next page 1 tag earlier.
			tags_to_next_entry -= 1			

		if not is_post_deleted:
			footer_tag = post_contents_tag.getnext()

		try:
			author = 'Author: ' + post_tag[0][2][0].text
		except IndexError:
			# Fallback option, probably due to an anonymous post
			author = 'Author: ' + post_tag[0][0].get('alt')
		post_content = convert_html_content(etree.tostring(post_contents_tag[0][0]).decode('utf-8'))

		# Also download any images shown in the post
		for image_tag in post_contents_tag[0][0].iterfind(".//img"):
			imageDumpDirectory = pathThusFar + '/Attachments'
			if not os.path.exists(imageDumpDirectory):
				imageDumpDirectory = makeDirectories(imageDumpDirectory)

			image_URL = image_tag.get('src')

			# For some reason there can be images containing nothing on a page. No idea why.
			if image_URL is None: 
				continue

			# Special case for relative URL's: drop the It's Learning root URL in front of it
			if not image_URL.startswith('http'):
				image_URL = itslearning_root_url + image_URL

			download_file(image_URL, imageDumpDirectory, session)

			delay()

		if not is_post_deleted:
			timestamp = footer_tag[0][0][0].text.strip()
		else:
			timestamp = ''

		fileContents += author + '\n' + timestamp + '\n\n' + post_content + '\n\n'

	bytesToTextFile(fileContents.encode('utf-8'), completeDumpFile + output_text_extension)

	# Add a time delay before moving on to the next post
	delay()

def processDiscussionForum(pathThusFar, discussionURL, session):
	discussion_response = session.get(discussionURL, allow_redirects=True)
	discussion_document = fromstring(discussion_response.text)

	# They are sooo inconsistent with these conventions.
	discussion_title = sanitiseFilename(discussion_document.get_element_by_id('ctl05_TT').text)

	print("\tDownloaded discussion:", discussion_title.encode('ascii', 'ignore'))

	discussionDumpDirectory = pathThusFar + '/Discussion - ' + discussion_title
	discussionDumpDirectory = sanitisePath(discussionDumpDirectory)
	discussionDumpDirectory = makeDirectories(discussionDumpDirectory)


	# hacky way of retrieving the discussion ID, which we need for fetching the threads.
	discussionID = discussionURL.split('=')[1]

	# ThreadID starts counting at 1 because ID 0 is the table header.
	threadID = 1
	pages_remaining = True

	# Pagination
	while pages_remaining:

		nextThreadElement = discussion_document.get_element_by_id('Threads_' + str(threadID))
		if nextThreadElement[0].text is None or (not nextThreadElement[0].text.startswith('No threads') and not nextThreadElement[0].text.startswith('Ingen hovedinnlegg')):
			while nextThreadElement is not None and nextThreadElement != False:
				postURL = nextThreadElement[1][0].get('href')
				postTitle = nextThreadElement[1][0].text
				processDiscussionPost(discussionDumpDirectory, itslearning_root_url + postURL, postTitle, session)
				threadID += 1
				try:
					nextThreadElement = discussion_document.get_element_by_id('Threads_' + str(threadID))
				except KeyError:
					nextThreadElement = False
		else:
			bytesToTextFile('No threads were created in this forum.'.encode('utf-8'), discussionDumpDirectory + '/No threads.txt')

		# Move on to next page
		found_next_page, discussion_response = loadPaginationPage(discussionURL, discussion_document, backpatch_character_index=7)

		if found_next_page:
			discussion_document = fromstring(discussion_response.text)
			# Start at the first thread on the next page
			threadID = 1
		else:
			pages_remaining = False



def processAssignment(pathThusFar, assignmentURL, session):
	print("\tDownloading assignment:", assignmentURL.encode('ascii', 'ignore'))
	assignment_response = session.get(assignmentURL, allow_redirects=True)
	assignment_document = fromstring(assignment_response.text)
	#writeHTML(assignment_document, 'output.html')

	assignment_title = assignment_document.get_element_by_id('ctl05_TT').text

	dumpDirectory = pathThusFar + '/Assignment - ' + assignment_title
	dumpDirectory = sanitisePath(dumpDirectory)
	dumpDirectory = makeDirectories(dumpDirectory)

	assignment_answer_table = assignment_document.find_class('itsl-assignment-answer')
	
	# Download the assignment description
	details_sidebar_element = assignment_document.find_class('ccl-rwgm-column-1-3')[0]
	description_element = assignment_document.find_class('ccl-rwgm-column-2-3')[0]

	assignment_description = convert_html_content(etree.tostring(description_element[1], encoding='utf-8').decode('utf-8'))
	
	details_element = details_sidebar_element[1]
	assignment_details = ''

	for element in details_element:
		# Just dump the table on the right sidebar as-is
		assignment_details += ' '.join(convert_html_content(element.text_content()).split('\n')).strip() + '\n'

	assignment_details += '\nTask description:\n\n' + assignment_description

	bytesToTextFile(assignment_details.encode('utf-8'), dumpDirectory + '/Assignment description' + output_text_extension)

	# Download assignment description files
	file_listing_element = description_element[2][1]
	for file_element in file_listing_element:
		file_url = file_element[0].get('href')
		download_file(file_url, dumpDirectory, session)


	# Download own submission, but only if assignment was answered
	if assignment_answer_table:
		answerDumpDirectory = dumpDirectory + '/Own answer'
		answerDumpDirectory = makeDirectories(answerDumpDirectory)

		# For some reason not all answers have a tbody tag.
		assignment_answer_root = assignment_answer_table[0]
		if assignment_answer_root[0].tag == 'tbody':
			assignment_answer_root = assignment_answer_root[0]

		for entry in assignment_answer_root:

			if entry is None or entry[0] is None or entry[0].text is None:
				continue

			if entry[0].text.startswith('Comment'):
				bytesToTextFile(etree.tostring(entry[1], encoding='utf-8'), answerDumpDirectory + '/comment.html')
			elif entry[0].text.startswith('Assessment'):
				bytesToTextFile(entry[1].text.encode('utf-8'), answerDumpDirectory + '/assessment.html')
			elif entry[0].text.startswith('Answer'):
				bytesToTextFile(etree.tostring(entry[1], encoding='utf-8'), answerDumpDirectory + '/answer_comment.html')
			elif entry[0].text.startswith('Files'):
				file_list_div = entry[1][0]
				for index, file_entry in enumerate(file_list_div):
					if file_entry.tag == 'section':
						continue
					if len(file_entry) == 0:
						continue

					file_index = None
					if len(file_list_div) > 2:
						file_index = index

					file_location = file_entry[0][0].get('href')
					download_file(file_location, answerDumpDirectory, session, file_index)

	answers_submitted = True
	try:
		assignment_document.get_element_by_id('EssayAnswers_0')
	except KeyError:
		answers_submitted = False

	if answers_submitted:
		

		student_submissions = dumpDirectory + '/Student answers'
		student_submissions = makeDirectories(student_submissions)

		# Index 0 is the table header, which we skip

		pages_remaining = True
		while pages_remaining:
			submission_index = 1
			answers_remaining = True
			while answers_remaining:
				try:
					submission_element = assignment_document.get_element_by_id('EssayAnswers_{}'.format(submission_index))
				except KeyError:
					# End the loop when there are no more submissions

					answers_remaining = False
					continue

				#for i in range(0, 10):
				#	try: 
				#		print(i, ':', etree.tostring(submission_element[i]))
				#	except IndexError:
				#		pass
						
				no_group_index_offset = 0
				if 'No group' in submission_element[2].text_content():
					no_group_index_offset = 1
				elif 'Manage' in submission_element[2].text_content():
					no_group_index_offset = 1
				elif 'New group' in submission_element[2].text_content():
					no_group_index_offset = 1

				#print("Index offset:", no_group_index_offset)

				# Exploits that solution links have no text with coloured highlighting
				try:
					plagiarism_text_element = submission_element[6 + no_group_index_offset][0]
					has_plagiarism_report = plagiarism_text_element.get('class') is not None and ('colorbox' in plagiarism_text_element.get('class') or 'h-hidden' in plagiarism_text_element.get('class'))
				except IndexError:
					has_plagiarism_report = False

				plagiarism_index_offset = 0
				if has_plagiarism_report:
					plagiarism_index_offset = 1

				#print('plagiarism offset:', plagiarism_index_offset)


				# Column 0: Checkbox
				# Column 1: Student names
				students = [link[0].text for link in submission_element[1].find_class('ccl-iconlink')]
				# Column 2: Submission date/time
				submission_time = submission_element[2 + no_group_index_offset].text
				# Column 3: Review date
				review_date = submission_element[3 + no_group_index_offset].text
				# Column 4: Status
				status = submission_element[4 + no_group_index_offset].text_content()
				# Column 5: Score
				# If nobody answered the assignment, all of the next elements are not present and thus will fail
				try:
					score = submission_element[5 + no_group_index_offset].text
				except IndexError:
					score = None
				# Column 6: Plagiarism status
				if has_plagiarism_report:
					try:
						plagiarism_status = submission_element[6 + no_group_index_offset].text_content()
					except IndexError:
						plagiarism_status = None
				else:
					plagiarism_status = None
				# Column 7: Show (link to details page)
				try:
					details_page_url = itslearning_root_url + submission_element[6 + no_group_index_offset + plagiarism_index_offset][0].get('href')
				except IndexError:
					details_page_url = None

				has_submitted = submission_time is not None and not 'Not submitted' in submission_time and not 'Ikke levert' in submission_time
				if submission_time is None:
					submission_time = 'Not submitted.'
				if review_date is None:
					review_date = 'Not assessed.'
				if score is None:
					score = ''
				if plagiarism_status is None:
					plagiarism_status = 'No plagiarism check has been done.'


				print('\tDownloading assignment submission ', students[0].encode('ascii', 'ignore'))

				comment_field_contents = ''
				details_page_content = None

				# Only download solution if one was submitted
				if has_submitted:
					details_page_response = session.get(details_page_url, allow_redirects = True)
					details_page_content = fromstring(details_page_response.content)

					assessment_form_element = details_page_content.get_element_by_id('AssessForm')

					comment_field_element = assessment_form_element.get_element_by_id('AssessForm_comments_EditorCKEditor_ctl00')
					comment_field_contents = convert_html_content(etree.tostring(comment_field_element).decode('utf-8'))
				
				answer_directory = student_submissions + '/' + sanitiseFilename(students[0])
				answer_directory = makeDirectories(answer_directory)

				# Write out assessment details to a file
				answer_info = 'Students:\n'
				for student in students:
					answer_info += '\t- ' + student + '\n'
				answer_info += 'Submission Time: ' + submission_time + '\n'
				answer_info += 'Review Date: ' + review_date + '\n'
				answer_info += 'Status: ' + status + '\n'
				answer_info += 'Score: ' + score + '\n'
				answer_info += 'Plagiarism status: ' + plagiarism_status + '\n'
				answer_info += 'Comments on assessment: \n\n' + comment_field_contents + '\n'

				bytesToTextFile(answer_info.encode('utf-8'), answer_directory + '/answer' + output_text_extension)

				# Again, only download files if there is a submission in the first place.
				if has_submitted:
					# Case 1: A plagiarism check was performed
					has_checked_files = True
					try:
						file_listing_element = assessment_form_element.find_class('tablelisting')[0][0]
					except IndexError:
						has_checked_files = False
					if has_checked_files:
						for link in file_listing_element.iterlinks():
							# We only want URLs for files.
							# Contrary to what it might seem iterlinks iterates over anything with an external URL in it.
							if not link[0].tag == 'a':
								continue
							# We also don't want plagiarism reports
							if '/essay/PlagiarismReport.aspx' in link[2]:
								continue
							download_file(link[2], answer_directory, session, filename=html.unescape(link[0].text_content()), disableFilenameReencode=True)
					
					# Case 2: No plagiarism check was performed
					has_unchecked_files = True
					try:
						file_listing_element = assessment_form_element.get_element_by_id('AssessForm_ctl02_FileList')[1]
					except KeyError:
						has_unchecked_files = False
					if has_unchecked_files:
						for link_element in file_listing_element:
							download_file(link_element[0].get('href'), answer_directory, session, filename=html.unescape(link_element[0].text_content()), disableFilenameReencode=True)


				
				submission_index += 1

			# Move on to the next page
			found_next_page, assignment_response = loadPaginationPage(assignmentURL, assignment_document, backpatch_character_index=12)

			if found_next_page:
				assignment_document = fromstring(assignment_response.text)
			else:
				pages_remaining = False



def processFile(pathThusFar, fileURL, session):
	file_response = session.get(fileURL, allow_redirects=True)

	#writeHTML(file_response, 'output.html')
	# Find all download links
	
	download_link_indices = [m.start() for m in re.finditer('/file/download\.aspx\?FileID=', file_response.text)]

	if len(download_link_indices) > 1:
		print('\tMultiple versions of file were found on page.')

	# Download each of them
	for index, link_start_index in enumerate(download_link_indices):
		link_end_index = file_response.text.find('"', link_start_index + 1)
		file_index = None
		if len(download_link_indices) > 1:
			file_index = index
			print('\tDownloading version {} of {}.'.format(index+1, len(download_link_indices)))
		
		download_file('https://ntnu.itslearning.com' + file_response.text[link_start_index:link_end_index], pathThusFar, session, file_index)

def processFolder(pathThusFar, folderURL, session, courseIndex, folder_state = [], level = 0, catch_up_state = None):
	print("\tDumping folder: ", pathThusFar.encode('ascii', 'ignore'))
	pathThusFar = sanitisePath(pathThusFar)
	if not os.path.exists(pathThusFar):
		pathThusFar = makeDirectories(pathThusFar)

	folder_response = session.get(folderURL, allow_redirects=True)
	#writeHTML(folder_response, 'output.html')
	folder_response_document = fromstring(folder_response.text)

	folder_contents_table = folder_response_document.get_element_by_id('ctl00_ContentPlaceHolder_ProcessFolderGrid_T')
	folder_contents_tbody = folder_contents_table[1]

	if folder_contents_tbody[0][0].get('class') == 'emptytablecell':
		print('\tFolder is empty.')
		return

	item_title_column = 1
	if folder_contents_table[0][0][0].get('class') == 'selectcolumn':
		item_title_column = 2

	for index, folder_contents_entry in enumerate(folder_contents_tbody):
		
		if catch_up_state is not None:
			target_course_id = catch_up_state[0]
			target_folder_state = catch_up_state[1]
			# We only want to fast-forward within the course we're catching up to
			if target_course_id == courseIndex and index < len(target_folder_state) and index < target_folder_state[level]:
				print('\tSkipping item to resume from saved state.')
				continue

		# Write the current status file (saves progress)
		if enable_checkpoints:
			if os.path.exists(progress_file_location):
				os.remove(progress_file_location)

			progress_file_contents = (str(courseIndex) + '\n' + ', '.join([str(i) for i in folder_state + [index]])).encode('utf-8')
			with open(progress_file_location, 'wb') as state_file:
				state_file.write(progress_file_contents)

		item_name = folder_contents_entry[item_title_column][0].text
		item_url = folder_contents_entry[item_title_column][0].get('href')

		if item_url.startswith('/Folder'):
			folderURL = itslearning_folder_base_url + item_url.split('=')[1]
			processFolder(pathThusFar + "/Folder - " + item_name, folderURL, session, courseIndex, folder_state + [index], level + 1)
		elif item_url.startswith('/File'):
			pass
			processFile(pathThusFar, itslearning_file_base_url + item_url.split('=')[1], session)
		elif item_url.startswith('/essay'):
			pass
			processAssignment(pathThusFar, itslearning_assignment_base_url + item_url.split('=')[1], session)
		elif item_url.startswith('/note'):
			pass
			processNote(pathThusFar, itslearning_note_base_url + item_url.split('=')[1], session)
		elif item_url.startswith('/discussion'):
			pass
			processDiscussionForum(pathThusFar, itslearning_discussion_base_url + item_url.split('=')[1], session)
		elif item_url.startswith('/weblink'):
			pass
			processWeblink(pathThusFar, itslearning_weblink_base_url + item_url.split('=')[1], item_name, session)
		elif item_url.startswith('/LearningToolElement'):
			pass
			processLearningToolElement(pathThusFar, itslearning_learning_tool_base_url + item_url.split('=')[1], session)
		elif item_url.startswith('/test'):
			pass
			processTest(pathThusFar, itslearning_test_base_url + item_url.split('=')[1], session)
		elif item_url.startswith('/picture'):
			pass
			processPicture(pathThusFar, itslearning_picture_url.format(item_url.split('=')[1]), session)
		else:
			print('Warning: Skipping unknown URL:', item_url.encode('ascii', 'ignore'))

		# Ensure some delay has occurred so that we are not spamming when querying lots of empty folders.
		delay()

def loadMessagingPage(index, session):
	url = 'https://ntnu.itslearning.com/restapi/personal/instantmessages/messagethreads/v1?threadPage={}&maxThreadCount=15'.format(index)
	return json.loads(session.get(url, allow_redirects=True).text)

def processMessaging(pathThusFar, session):
	batchIndex = 0
	threadIndex = 0
	messageBatch = loadMessagingPage(batchIndex, session)

	dumpDirectory = pathThusFar + 'Messaging/New API'
	dumpDirectory = makeDirectories(dumpDirectory)
	attachmentsDirectory = dumpDirectory + '/Attachments'
	attachmentsDirectory = makeDirectories(attachmentsDirectory)

	print('Downloading messages (sent through the new API)')

	while len(messageBatch['EntityArray']) > 0:
		print('\tDownloading message batch {}'.format(batchIndex))
		for messageThread in messageBatch['EntityArray']:
			threadFileContents = ''
			for message in messageThread['Messages']['EntityArray']:
				threadFileContents += 'From: ' + html.unescape(message['CreatedByName']) + '\n'
				threadFileContents += 'Sent on: ' + html.unescape(message['CreatedFormatted']) + '\n'
				if message['AttachmentName'] is not None:
					threadFileContents += 'Attachment: ' + html.unescape(message['AttachmentName']) + '\n'
				threadFileContents += '\n'
				threadFileContents += html.unescape(message['Text']) + '\n'
				threadFileContents += '\n'
				threadFileContents += '-------------------------------------------------------------------------\n'
				
				if message['AttachmentName'] is not None:
					download_file(message['AttachmentUrl'], attachmentsDirectory, session, index=None, filename=None)#str(message['InstantMessageThreadId']) + '_' + message['AttachmentName'])
			thread_title = 'Message thread ' + str(threadIndex) + ' - ' + sanitiseFilename(messageThread['Created']) + '.txt'
			threadFileContents = threadFileContents.encode('utf-8')
			bytesToTextFile(threadFileContents, dumpDirectory + '/' + thread_title)
			threadIndex += 1

		delay()
		batchIndex += 1
		messageBatch = loadMessagingPage(batchIndex, session)

	print('Downloading messages (send through the old API)')

	dumpDirectory = pathThusFar + 'Messaging/Old API'
	dumpDirectory = makeDirectories(dumpDirectory)
	
	
	folderID = 1
	messaging_response = session.get(old_messaging_api_url.format(folderID), allow_redirects=True)

	while messaging_response.url != itslearning_not_found:
		inbox_document = fromstring(messaging_response.text)
		inbox_title = inbox_document.get_element_by_id('ctl05_TT').text_content()
		print('\tAccessing folder {}'.format(inbox_title).encode('ascii', 'ignore'))
		
		boxDirectory = dumpDirectory + '/' + sanitiseFilename(inbox_title)
		boxDirectory = makeDirectories(boxDirectory)
		attachmentsDirectory = boxDirectory + '/Attachments'
		attachmentsDirectory = makeDirectories(attachmentsDirectory)

		pagesRemain = True
		message_index = 1
		message_index_on_page = 1
		while pagesRemain:

			# Needed to dig into a bunch of nested div's here.
			messages_remaining = True
			while messages_remaining:
				print('\tDownloading message {}'.format(message_index))
				try:
					message_element = inbox_document.get_element_by_id('_table_{}'.format(message_index_on_page))
					# Index 0: Checkbox
					# Index 1: Favourite star
					# index 2: Sender
					# Index 3: Title
					message_url = itslearning_root_url + message_element[3][0].get('href')
					message_response = session.get(message_url, allow_redirects = True)
					message_document = fromstring(message_response.text)

					has_attachment = len(message_element[4]) != 0

					
					# There's a distinction between sent/received and unsent ones. In the latter case we need to grab the message from the editor
					if 'sendmessage.aspx' in message_response.url:
						form_root = message_document.get_element_by_id('_inputForm')
						message_recipient = form_root[0][0][0][0][1].text_content()
						message_recipient += ' ' + form_root[0][0][1][0][1].text_content()
						message_sender = '[you]'
						message_title = convert_html_content(etree.tostring(form_root[0][0][2][0][1], encoding='utf8').decode('utf-8'))
						message_body = convert_html_content(etree.tostring(form_root.get_element_by_id('_inputForm_MessageText_MessageTextEditorCKEditor_ctl00'), encoding='utf8').decode('utf-8'))
						message_send_date = 'N/A'
						if has_attachment:
							print('ATTACHMENTS IN UNSENT MESSAGES ARE NOT SUPPORTED :(')
					else:
						message_title = message_document.get_element_by_id('ctl05_TT').text_content()
						# Eventually these indexing series will form a binarised version of the entire works of shakespeare
						message_header_element = message_document.find_class('readMessageHeader')[0][1]
						message_sender = convert_html_content(message_header_element[0][1].text_content())
						message_recipient = convert_html_content(message_header_element[1][1].text_content())
						message_body = convert_html_content(etree.tostring(message_document.find_class('readMessageBody')[0][1][0][0][0], encoding='utf8').decode('utf-8'))
						# It's Learning system messages have no link to the sender
						if len(message_header_element[0][1]) == 0:
							message_send_date = message_header_element[0][1].text_content()
						else:
							message_send_date = message_header_element[0][1][0].tail
						if has_attachment:
							attachment_filename = message_header_element[2][1][0].text_content()
							message_attachment_url = message_header_element[2][1][0].get('href')
							download_file(itslearning_root_url + message_attachment_url, attachmentsDirectory, session, index=None, filename=attachment_filename, disableFilenameReencode=True)

					message_file_contents = 'From: ' + message_sender + '\n'
					message_file_contents = 'To: ' + message_recipient + '\n'
					message_file_contents += 'Subject: ' + message_title + '\n'
					message_file_contents += 'Sent on: ' + message_send_date + '\n'
					if has_attachment:
						message_file_contents += 'Attachment: ' + attachment_filename
					message_file_contents += 'Message contents: \n\n' + html.unescape(message_body)

					bytesToTextFile(message_file_contents.encode('utf-8'), boxDirectory + '/Message ' + str(message_index) + ' - ' + sanitiseFilename(message_send_date) + output_text_extension)

					delay()
					# Index 4: Has asttachments
					# Index 5: Received on
				except KeyError:
					# End the loop when there are no more messages
					messages_remaining = False
					continue
				
				message_index_on_page += 1
				message_index += 1

			# Move on to the next page
			found_next_page, messaging_response = loadPaginationPage(old_messaging_api_url.format(folderID), inbox_document)

			if found_next_page:
				inbox_document = fromstring(messaging_response.text)
				message_index_on_page = 1
			else:
				pagesRemain = False

		folderID += 1
		messaging_response = session.get(old_messaging_api_url.format(folderID), allow_redirects=True)

def dumpSingleBulletin(raw_page_text, bulletin_element, dumpDirectory, bulletin_index):
	# Post data
	author = bulletin_element.find_class('itsl-light-bulletins-person-name')[0][0][0].text_content()
	print('\tBulletin by', author.encode('ascii', 'ignore'))
	post_content = convert_html_content(bulletin_element.find_class('h-userinput itsl-light-bulletins-list-item-text')[0].get('data-text'))

	bulletin_file_content = 'Author: ' + author + '\n\n' + post_content

	# Comments
	# This is so hacky, you better not look for a moment
	# Here we get a specific line of javascript code containing a JSON object with all information we need
	bulletin_id = bulletin_element[0].get('data-bulletin-id')
	search_string = 'CCL.CommentModule[\'CommentModule_LightBulletin_' + str(bulletin_id) + '_CommentModule\'] = true;'

	code_start_index = raw_page_text.index(search_string)
	json_line_start_index = raw_page_text.index('\n', code_start_index)
	json_line_end_index = raw_page_text.index('\n', json_line_start_index + 1)
	json_line = raw_page_text[json_line_start_index:json_line_end_index].strip()
	
	# Cut the JSON object out of the line
	json_object_start_index = json_line.index('{')
	json_object_string = json_line[json_object_start_index:-2]
	
	# Parse the json object string
	comment_info = json.loads(json_object_string)

	# Only dump comments if there are any
	if comment_info['DataSource']['VirtualCount'] > 0:
		bulletin_file_content += '\n\n\n ---------- Comments ----------\n\n'
		for comment in comment_info['DataSource']['Items']:
			bulletin_file_content += 'Comment by: ' + comment['UserName'] + '\n'
			bulletin_file_content += 'Posted: ' + comment['DateTimeTooltip'] + '\n\n'
			bulletin_file_content += comment['CommentText'] + '\n\n'
			bulletin_file_content += ' -----\n\n'


		# If we didn't get all comments, load the rest
		if len(comment_info['DataSource']['Items']) < comment_info['DataSource']['VirtualCount']:
			sourceID = comment_info['UserData']['sourceId']
			sourceType = comment_info['UserData']['sourceType']
			# The comment ID seems to be the first in the list of comments
			commentId = comment_info['DataSource']['Items'][0]['Id']
			# Try to get all at once
			count = comment_info['DataSource']['VirtualCount']
			readItemsCount = comment_info['NumberOfPreviouslyReadItemsToDisplay']
			useLastName = comment_info['UsePersonNameFormatLastFirst']

			complete_comment_url = itslearning_comment_service.format(sourceID, sourceType, commentId, count, readItemsCount, useLastName)
			additional_comments = json.loads(session.get(complete_comment_url, allow_redirects=True).text)

			delay()

			for additional_comment in additional_comments['Items']:
				bulletin_file_content += 'Comment by: ' + additional_comment['UserName'] + '\n'
				bulletin_file_content += 'Posted: ' + additional_comment['DateTimeTooltip'] + '\n\n'
				bulletin_file_content += additional_comment['CommentText'] + '\n\n'
				bulletin_file_content += ' -----\n\n'

	bytesToTextFile(bulletin_file_content.encode('utf-8'), dumpDirectory + '/Bulletin ' + str(bulletin_index) + output_text_extension)

def processBulletins(pathThusFar, courseURL, session, courseID):
	bulletin_response = session.get(courseURL, allow_redirects=True)
	bulletin_document = fromstring(bulletin_response.text)

	is_new_style_bulletins = True

	# Test for what kinds of bulletins we're dealing with.
	# Basically just requesting lots of stuff that only exists in the new version and catching any errors produced
	try:
		attribute_value = bulletin_document.get_element_by_id('ctl00_ContentPlaceHolder_DashboardLayout_ctl04_ctl03_CT')[0][0].get('data-bulletin-item-editor-template')
		is_new_style_bulletins = attribute_value is not None
	except IndexError:
		is_new_style_bulletins = False

	if is_new_style_bulletins:
		bulletin_list_element = bulletin_document.get_element_by_id('ctl00_ContentPlaceHolder_DashboardLayout_ctl04_ctl03_CT')[0][0]

		# Don't dump bulletins if there aren't any
		if 'No bulletins' in bulletin_list_element[0].text_content() or 'Ingen oppslag' in bulletin_list_element[0].text_content():
			return

		dumpDirectory = pathThusFar + '/Bulletins'
		dumpDirectory = makeDirectories(dumpDirectory)

		bulletin_id = 0

		for index, bulletin_element in enumerate(bulletin_list_element):
			# Skip the box for writing a new bulletin
			if index == 0 and 'itsl-light-bulletins-new-item-listitem' in bulletin_element.get('class'):
				continue

			bulletin_id += 1

			dumpSingleBulletin(bulletin_response.text, bulletin_element, dumpDirectory, bulletin_id)

		# Get initial next page settings
		field_name = '"InitialPageData"'
		json_field_start_index = bulletin_response.text.index(field_name)
		json_field_end_index = bulletin_response.text.index('}', json_field_start_index)
		next_bulletin_batch_string = '{' + bulletin_response.text[json_field_start_index:json_field_end_index] + '} }'
		next_bulletin_batch = json.loads(next_bulletin_batch_string)['InitialPageData']

		# Now we keep going until all bulletins have been downloaded
		while next_bulletin_batch['NeedToShowMore']:
			print('\tLoading more bulletins')
			additional_bulletins_response = session.get(itslearning_bulletin_next_url.format(courseID, next_bulletin_batch['BoundaryLightBulletinId'], next_bulletin_batch['BoundaryLightBulletinCreatedTicks']))
			additional_bulletins_document = fromstring(additional_bulletins_response.text)

			for bulletin_element in additional_bulletins_document:
				# Final element means we need to extract the metadata to request the next page
				if bulletin_element.get('data-pagedata') is not None and 'NeedToShowMore' in bulletin_element.get('data-pagedata'):
					next_bulletin_batch = json.loads(html.unescape(bulletin_element.get('data-pagedata')))
					break

				bulletin_id += 1
				dumpSingleBulletin(additional_bulletins_response.text, bulletin_element, dumpDirectory, bulletin_id)

			delay()
	bulletin_list_elements1 = bulletin_document.xpath('//div[@id = $elementid]', elementid = 'ctl00_ContentPlaceHolder_DashboardLayout_ctl04_ctl04_CT')
	bulletin_list_elements2 = bulletin_document.xpath('//div[@id = $elementid]', elementid = 'ctl00_ContentPlaceHolder_DashboardLayout_ctl04_ctl03_CT')
	bulletin_list_elements = [i.find_class('itsl-cb-news-old-bulletin-list') for i in (bulletin_list_elements1 + bulletin_list_elements2)]
	bulletin_list_elements = [item for sublist in bulletin_list_elements for item in sublist]

	text_elements = [i for i in (bulletin_list_elements1 + bulletin_list_elements2) if 'ilw-cb-text' in i.getparent().getparent().get('class')]

	is_old_style_bulletin = len(bulletin_list_elements) > 0 or len(text_elements) > 0

	if is_old_style_bulletin:
		# Some pages seem to be using one or the other, or both. A slow migration thing perhaps?
		
		message_count_thus_far = 0
		dumpDirectory = pathThusFar + '/Bulletins'

		for text_element in text_elements:
			# We found a text message
			print('\tFound text message')
			message_count_thus_far += 1

			try:
				message_title = text_element.getparent().getprevious()[0][0][0].text_content()
				message_content = convert_html_content(etree.tostring(text_element[0], encoding='utf-8').decode('utf-8')).strip()
				
				textDumpDirectory = dumpDirectory + '/Text messages'
				if not os.path.exists(textDumpDirectory):
					textDumpDirectory = makeDirectories(textDumpDirectory)

				message_file_contents = message_title + '\n\n' + message_content
			except IndexError:
				print('Failed to dump text message. Might be some other old-style course page element the script doesn\'t know about.')
				return

			bytesToTextFile(message_file_contents.encode('utf-8'), textDumpDirectory + '/Message ' + str(message_count_thus_far) + output_text_extension)

		for bulletin_list_element in bulletin_list_elements:

			# Special case for an occurrence of an empty element.
			if len(bulletin_list_element) == 0 or len(bulletin_list_element[0]) == 0:
				return
			elif bulletin_list_element.tag == 'ul':
				# We found a bulletin list

				if 'No bulletins' in bulletin_list_element[0].text_content() or 'Ingen oppslag' in bulletin_list_element[0].text_content():
					return

				if not os.path.exists(dumpDirectory):
					dumpDirectory = makeDirectories(dumpDirectory)

				bulletin_id = 0
				for list_element in bulletin_list_element:
					bulletin_id += 1

					bulletin_subject = convert_html_content(list_element[0].text_content()).strip()
					bulletin_message = convert_html_content(etree.tostring(list_element[1], encoding='utf-8').decode('utf-8')).strip()
					bulletin_author = convert_html_content(list_element[3][0].text_content()).strip()
					bulletin_post_date = convert_html_content(list_element[3][1].text_content()).strip()

					bulletin_file_content = 'Author: ' + bulletin_author + '\n'
					bulletin_file_content += 'Posted on: ' + bulletin_post_date + '\n'
					bulletin_file_content += 'Subject: ' + bulletin_subject + '\n'
					bulletin_file_content += 'Message:\n\n' + bulletin_message

					print('\tSaving bulletin by:', bulletin_author.encode('ascii', 'ignore'))

					file_path = dumpDirectory + '/Bulletin ' + str(bulletin_id) + output_text_extension

					bytesToTextFile(bulletin_file_content.encode('utf-8'), file_path)

					# No support for comments here. I couldn't find any course that had them.















# --- MAIN PROGRAM ---

if os.path.exists(output_folder_name):
	print('The output folder already exists. This might happen if you run the script again after running it once.')
	print('This script does not support "catching up" if it crashed or was stopped previously.')
	print('Please type exactly \'delete\' to remove the folder and start over. Type something else to abort.')
	decision = input('Confirm deletion: ')
	if not decision == 'delete':
		sys.exit("Download Aborted.")
	rmtree(output_folder_name)

catch_up_directions = None
if os.path.exists(progress_file_location):
	print('It appears you have run this script previously. Would you like to continue where you left off?')
	print('Type "continue" to fast-forward to where you left off. Type anything else to start over.')
	decision = input('Confirm fast-forward: ')
	if decision == 'continue':
		print('Loading saved state file.')
		with open(progress_file_location) as input_file:
			file_contents = input_file.readlines() 
		state_course_id = int(file_contents[0])
		state_folder_state = [int(i) for i in file_contents[1].split(', ')]
		catch_up_directions = [state_course_id, state_folder_state]

with requests.Session() as session:

	print('Querying Innsida..')
	response = session.get(innsida, params=innsida_login_parameters, allow_redirects=True)

	login_page = fromstring(response.text)

	login_form = login_page.forms[0]
	
	login_form.fields['feidename'] = ntnu_user
	login_form.fields['password'] = ntnu_pass

	login_form_dict = convert_lxml_form_to_requests(login_form)

	feide_login_submit_url = feide_base_url + login_form.action

	print('Sending login data')

	relay_response = session.post(feide_login_submit_url, data = login_form_dict)

	innsida_main_page = do_feide_relay(relay_response)

	print('Accessing It\'s Learning')

	innsida_outgoing_response = session.get(itslearning_url, allow_redirects = True)

	# Same story as before. The page goes through FEIDE, which has a built-in form we need to auto-submit

	itslearning_main_page = do_feide_relay(innsida_outgoing_response)

	print('Listing courses')

	# Part 1: Obtain session-specific form

	course_list_response = session.get(itsleaning_course_list, allow_redirects = True)
	course_list_page = fromstring(course_list_response.text)
	course_list_form = course_list_page.forms[0]
	
	course_list_form.fields['ctl26$ctl00$ctl25$ctl02'] = 'All'
	course_list_dict = convert_lxml_form_to_requests(course_list_form)

	# Part 2: Show all courses

	all_courses_response = session.post(itsleaning_course_list, data=course_list_dict, allow_redirects = True)
	all_courses_page = fromstring(all_courses_response.text)

	# Part 3: Extract the course names

	courseList = []
	courseNameDict = {}

	# Not a great way of doing this; assumes page structure. Should work for the very near future though.
	courseTableDivElement = all_courses_page.find_class('tablelisting')[1]
	courseTableElement = courseTableDivElement[0]
	for index, courseTableRowElement in enumerate(courseTableElement.getchildren()):
		if index == 0:
			continue
		# Extract the course ID from the URL
		courseURL = courseTableRowElement[2][0].get('href').split("=")[1]
		courseList.append(courseURL)
		courseNameDict[courseURL] = courseTableRowElement[2][0][0].text

	pathThusFar = output_folder_name

	print('Found', str(len(courseList)), 'courses.')

	# If it is desirable to skip to a particular course, also skip downloading the messages again
	if skip_to_course_with_index == 0 and catch_up_directions is None:
		processMessaging(pathThusFar, session)
	

	for courseIndex, courseURL in enumerate(courseList):
		print('Dumping course with ID {} ({} of {}): {}'.format(courseURL, (courseIndex + 1), len(courseList), courseNameDict[courseURL].encode('ascii', 'ignore')))
		if courseIndex + 1 < skip_to_course_with_index:
			continue
		if catch_up_directions is not None and courseIndex + 1 < catch_up_directions[0]:
			continue

		course_response = session.get(itslearning_course_base_url + "?LocationID=" + courseURL + "&LocationType=1", allow_redirects=True)

		root_folder_url_index = course_response.text.find(itslearning_folder_base_url)
		root_folder_end_index = course_response.text.find("'", root_folder_url_index + 1)
		root_folder_url = course_response.text[root_folder_url_index:root_folder_end_index]

		course_folder = pathThusFar + sanitiseFilename(courseNameDict[courseURL])

		processBulletins(course_folder, itslearning_bulletin_base_url + courseURL, session, courseURL)

		processFolder(course_folder, root_folder_url, session, courseIndex, catch_up_state=catch_up_directions)

	print('Done. Everything was downloaded successfully!')



	