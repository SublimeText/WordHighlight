import sublime
import sublime_plugin
import re
import time

settings = sublime.load_settings('Word Highlight.sublime-settings')
settings_base = sublime.load_settings('Base File.sublime-settings')

class Pref:
	def load(self):
		Pref.color_scope_name                                   	= settings.get('color_scope_name', "comment")
		Pref.selection_delay                                    	= settings.get('selection_delay', 0.04)
		Pref.draw_outlined                                      	= bool(settings.get('draw_outlined', True)) * sublime.DRAW_OUTLINED
		Pref.highlight_when_selection_is_empty                  	= bool(settings.get('highlight_when_selection_is_empty', False))
		Pref.highlight_word_under_cursor_when_selection_is_empty	= bool(settings.get('highlight_word_under_cursor_when_selection_is_empty', False))
		Pref.word_separators                                    	= settings_base.get('word_separators')
		Pref.file_size_limit                                    	= int(settings.get('file_size_limit', 4194304))
		Pref.timing                                             	= time.time()

Pref().load()

g_enabled = True

settings.add_on_change('color_scope_name',                                   	lambda:Pref().load())
settings.add_on_change('selection_delay',                                    	lambda:Pref().load())
settings.add_on_change('draw_outlined',                                      	lambda:Pref().load())
settings.add_on_change('highlight_when_selection_is_empty',                  	lambda:Pref().load())
settings.add_on_change('highlight_word_under_cursor_when_selection_is_empty',	lambda:Pref().load())
settings.add_on_change('file_size_limit',                                    	lambda:Pref().load())
settings_base.add_on_change('word_separators',                               	lambda:Pref().load())


class set_word_highlight_enabled(sublime_plugin.ApplicationCommand):
	def run(self, enabled=None):
		global g_enabled
		if enabled is None:
			enabled = not g_enabled
		g_enabled = enabled
	
	def description(self):
		return 'Disable' if g_enabled else 'Enable'


class SelectHighlightedWordsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		wh = self.view.get_regions("WordHighlight")
		for w in wh:
			self.view.sel().add(w)


class WordHighlightListener(sublime_plugin.EventListener):
	prev_regions = []

	def on_activated(self, view):
		if not view.is_loading():
			Pref.word_separators = view.settings().get('word_separators') or settings_base.get('word_separators')

	def on_selection_modified(self, view):
		if g_enabled and not view.settings().get('is_widget') and view.size() <= Pref.file_size_limit:
			now = time.time()
			if now - Pref.timing > Pref.selection_delay:
				self.highlight_occurences(view)
				Pref.timing = now
			else:
				Pref.timing = now
		elif not g_enabled:
			view.erase_regions("WordHighlight")

	def highlight_occurences(self, view):
		regions = []
		occurrencesMessage = []
		occurrencesCount = 0
		for sel in view.sel():
			if sel.empty() and Pref.highlight_when_selection_is_empty:
				string = view.substr(view.word(sel)).strip()
				if string and all([not c in Pref.word_separators for c in string]):
					regions += view.find_all('(?<![\\w])'+re.escape(string)+'\\b')
				if not Pref.highlight_word_under_cursor_when_selection_is_empty:
					for s in view.sel():
						regions = [r for r in regions if not r.contains(s)]
			else:
				word = view.word(sel)
				if word.end() == sel.end() and word.begin() == sel.begin() :
					string = view.substr(word).strip()
					if string:
						regions += view.find_all('(?<![\\w])'+re.escape(string)+'\\b')
			occurrences = len(regions)-occurrencesCount;
			if occurrences > 0:
				occurrencesMessage.append(str(occurrences) + ' occurrence' + ('s' if occurrences != 1 else '') + ' of "' + string + '"')
				occurrencesCount = occurrencesCount + occurrences
		if self.prev_regions != regions:
			view.erase_regions("WordHighlight")
			if regions:
				view.add_regions("WordHighlight", regions, Pref.color_scope_name, Pref.draw_outlined)
				view.set_status("WordHighlight", ", ".join(list(set(occurrencesMessage))))
			else:
				view.erase_status("WordHighlight")
			self.prev_regions = regions
