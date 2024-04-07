import re
import sys
import time

try:
	import thread
except:
	import _thread as thread

import sublime
import sublime_plugin

Pref = {}
settings_base = {}

def plugin_loaded():
	global settings_base
	global Pref

	settings = sublime.load_settings('Word Highlight.sublime-settings')
	if int(sublime.version()) >= 2174:
		settings_base = sublime.load_settings('Preferences.sublime-settings')
	else:
		settings_base = sublime.load_settings('Base File.sublime-settings')

	class Pref:
		def load(self):
			Pref.color_scope_name                                    = settings.get('color_scope_name', "comment")
			Pref.highlight_delay                                     = settings.get('highlight_delay', 0)
			Pref.case_sensitive                                      = (not bool(settings.get('case_sensitive', True))) * sublime.IGNORECASE
			Pref.draw_outlined                                       = bool(settings.get('draw_outlined', True)) * sublime.DRAW_OUTLINED
			Pref.mark_occurrences_on_gutter                          = bool(settings.get('mark_occurrences_on_gutter', False))
			Pref.icon_type_on_gutter                                 = settings.get("icon_type_on_gutter", "dot")
			Pref.highlight_when_selection_is_empty                   = bool(settings.get('highlight_when_selection_is_empty', False))
			Pref.highlight_word_under_cursor_when_selection_is_empty = bool(settings.get('highlight_word_under_cursor_when_selection_is_empty', False))
			Pref.highlight_non_word_characters                       = bool(settings.get('highlight_non_word_characters', False))
			Pref.word_separators                                     = settings_base.get('word_separators')
			Pref.show_status_bar_message                             = bool(settings.get('show_word_highlight_status_bar_message', True))
			Pref.file_size_limit                                     = int(settings.get('file_size_limit', 4194304))
			Pref.when_file_size_limit_search_this_num_of_characters  = int(settings.get('when_file_size_limit_search_this_num_of_characters', 20000))
			Pref.timing                                              = time.time()
			Pref.enabled                                             = bool(settings.get('enabled', True))
			Pref.prev_selections                                     = None
			Pref.prev_regions                                        = None
			Pref.select_next_word_skiped                             = 0

	Pref = Pref()
	Pref.load()

	settings.add_on_change('reload', lambda:Pref.load())
	settings_base.add_on_change('wordhighlight-reload', lambda:Pref.load())
	if Pref.highlight_when_selection_is_empty and not 'running_wh_loop' in globals():
		global running_wh_loop
		running_wh_loop = True
		thread.start_new_thread(wh_loop, ())

def wh_loop():
	while True:
		sublime.set_timeout(lambda:WordHighlightListener().on_selection_modified(sublime.active_window().active_view() if sublime.active_window() else None), 0)
		time.sleep(0.3)

# Backwards compatibility with Sublime 2.  sublime.version isn't available at module import time in Sublime 3.
if sys.version_info[0] == 2:
	plugin_loaded()


def escape_regex(str):
	# Sublime text chokes when regexes contain \', \<, \>, or \`.
	# Call re.escape to escape everything, and then unescape these four.
	str = re.escape(str)
	for c in "'<>`":
		str = str.replace('\\' + c, c)
	return str


def enabled(view):
	return Pref.enabled and \
			view and \
			not view.settings().get('is_widget') and \
			view.settings().get('word_highlight_enabled', True)

def updateEnabled(view):
	if not view:
		return
	if enabled(view):
		WordHighlightListener().highlight_occurences(view, forceUpdate=True)
	else:
		view.erase_regions("WordHighlight")


"""Toggles the global enable state
"""
class set_word_highlight_enabled(sublime_plugin.ApplicationCommand):
	def run(self):
		Pref.enabled = not Pref.enabled
		updateEnabled(sublime.active_window().active_view(), forceUpdate=True)

	def description(self):
		return 'Disable' if Pref.enabled else 'Enable'


"""Toggles per-view enable state
"""
class ToggleWordHighlightInViewCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		enabledInView = not self.view.settings().get('word_highlight_enabled', True)
		self.view.settings().set('word_highlight_enabled', enabledInView)
		updateEnabled(self.view)

	def is_enabled(self):
		return Pref.enabled

	def is_checked(self):
		return self.view.settings().get('word_highlight_enabled', True)

	def description(self):
		return 'Word Highlight'


class SelectHighlightedWordsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		wh = self.view.get_regions("WordHighlight")
		for w in wh:
			self.view.sel().add(w)

class SelectHighlightedNextWordCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = [s for s in self.view.sel()]
		sel.reverse()
		if sel:
			word = sel[0]
			wh = self.view.get_regions("WordHighlight")
			for w in wh:
				if w.end() > word.end() and w.end() > Pref.select_next_word_skiped:
					self.view.sel().add(w)
					self.view.show(w)
					Pref.select_next_word_skiped = w.end()
					break;

class SelectHighlightedSkipLastWordCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = [s for s in self.view.sel()]
		sel.reverse()
		if sel and len(sel) > 1:
			self.view.sel().subtract(sel[0])
			Pref.select_next_word_skiped = sel[0].end()

class WordHighlightClickCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		Pref.select_next_word_skiped = 0
		updateEnabled(self.view)


class WordHighlightListener(sublime_plugin.EventListener):
	def on_activated(self, view):
		Pref.prev_selections = None
		Pref.select_next_word_skiped = 0
		if not view.is_loading():
			Pref.word_separators = view.settings().get('word_separators') or settings_base.get('word_separators')
			updateEnabled(view)

	def on_selection_modified(self, view):
		if enabled(view):
			now = time.time()
			if now - Pref.timing > 0.08:
				Pref.timing = now
				sublime.set_timeout(lambda:self.highlight_occurences(view), 0)
			else:
				Pref.timing = now

	def set_status(self, view, message):
		if Pref.show_status_bar_message:
			view.set_status("WordHighlight", message)

	def highlight_occurences(self, view, forceUpdate=False):
		if not Pref.highlight_when_selection_is_empty and not view.has_non_empty_selection_region():
			view.erase_status("WordHighlight")
			view.erase_regions("WordHighlight")
			Pref.prev_regions = None
			Pref.prev_selections = None
			return
		# todo: The list cast below can go away when Sublime 3's Selection class implements __str__
		prev_selections = str(list(view.sel()))
		if Pref.prev_selections == prev_selections and not forceUpdate:
			return
		else:
			Pref.prev_selections = prev_selections

		if view.size() <= Pref.file_size_limit:
			limited_size = False
		else:
			limited_size = True

		# print 'running'+ str(time.time())

		regions = []
		processedWords = []
		occurrencesMessage = []
		occurrencesCount = 0
		for sel in view.sel():
			if Pref.highlight_when_selection_is_empty and sel.empty():
				string = view.substr(view.word(sel)).strip()
				if string not in processedWords:
					processedWords.append(string)
					if string and all([not c in Pref.word_separators for c in string]):
							regions = self.find_regions(view, regions, string, limited_size)
					if not Pref.highlight_word_under_cursor_when_selection_is_empty:
						for s in view.sel():
							regions = [r for r in regions if not r.contains(s)]
			elif not sel.empty() and Pref.highlight_non_word_characters:
				string = view.substr(sel)
				if string and string not in processedWords:
					processedWords.append(string)
					regions = self.find_regions(view, regions, string, limited_size)
			elif not sel.empty():
				word = view.word(sel)
				if word.end() == sel.end() and word.begin() == sel.begin():
					string = view.substr(word).strip()
					if string not in processedWords:
						processedWords.append(string)
						if string and all([not c in Pref.word_separators for c in string]):
								regions = self.find_regions(view, regions, string, limited_size)

			occurrences = len(regions)-occurrencesCount;
			if occurrences > 0:
				occurrencesMessage.append('"' + string + '" '+str(occurrences) +' ')
				occurrencesCount = occurrencesCount + occurrences
		if Pref.prev_regions != regions or forceUpdate:
			view.erase_regions("WordHighlight")
			if regions:
				if Pref.highlight_delay == 0:
					view.add_regions("WordHighlight", regions, Pref.color_scope_name, Pref.icon_type_on_gutter if Pref.mark_occurrences_on_gutter else "", Pref.draw_outlined)
					self.set_status(view, ", ".join(list(set(occurrencesMessage))) + (' found on a limited portion of the document ' if limited_size else ''))
				else:
					sublime.set_timeout(lambda:self.delayed_highlight(view, regions, occurrencesMessage, limited_size), Pref.highlight_delay)
			else:
				view.erase_status("WordHighlight")
			Pref.prev_regions = regions

	def find_regions(self, view, regions, string, limited_size):
		# It seems as if \b doesn't pay attention to word_separators, but
		# \w does. Hence we use lookaround assertions instead of \b.
		if Pref.highlight_non_word_characters:
			search = escape_regex(string)
		else:
			search = r'(?<!\w)'+escape_regex(string)+r'(?!\w)'

		if not limited_size:
			regions += view.find_all(search, Pref.case_sensitive)
		else:
			chars = Pref.when_file_size_limit_search_this_num_of_characters
			visible_region = view.visible_region()
			begin = 0 if visible_region.begin() - chars < 0 else visible_region.begin() - chars
			end = visible_region.end() + chars
			from_point = begin
			while True:
				region = view.find(search, from_point)
				if region:
					regions.append(region)
					if region.end() > end:
						break
					else:
						from_point = region.end()
				else:
					break
		return regions

	def delayed_highlight(self, view, regions, occurrencesMessage, limited_size):
		if regions == Pref.prev_regions:
			view.add_regions("WordHighlight", regions, Pref.color_scope_name, Pref.icon_type_on_gutter if Pref.mark_occurrences_on_gutter else "", Pref.draw_outlined)
			self.set_status(view, ", ".join(list(set(occurrencesMessage))) + (' found on a limited portion of the document ' if limited_size else ''))
