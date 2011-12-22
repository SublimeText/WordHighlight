import sublime
import sublime_plugin
import re
import time

settings = sublime.load_settings('Word Highlight.sublime-settings')

class Pref:
	def load(self):
		Pref.color_scope_name                                   	= settings.get('color_scope_name', "comment")
		Pref.selection_delay                                    	= settings.get('selection_delay', 0.04)
		Pref.draw_outlined                                      	= bool(settings.get('draw_outlined', True)) * sublime.DRAW_OUTLINED
		Pref.highlight_when_selection_is_empty                  	= bool(settings.get('highlight_when_selection_is_empty', False))
		Pref.highlight_word_under_cursor_when_selection_is_empty	= bool(settings.get('highlight_word_under_cursor_when_selection_is_empty', False))
		Pref.word_separators                                    	= []
		Pref.timing 																							= time.time()

Pref().load()

settings.add_on_change('color_scope_name',                  lambda:Pref().load())
settings.add_on_change('draw_outlined',                     lambda:Pref().load())
settings.add_on_change('highlight_when_selection_is_empty', lambda:Pref().load())


class SelectHighlightedWordsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		wh = self.view.get_regions("WordHighlight")
		for w in wh:
				self.view.sel().add(w)

class WordHighlightListener(sublime_plugin.EventListener):
	prev_regions = []

	def on_activate(self, view):
		Pref.word_separators = view.settings().get('word_separators')

	def on_selection_modified(self, view):
		if not view.settings().get('is_widget'):
			now = time.time()
			if now - Pref.timing > Pref.selection_delay:
				self.highlight_occurences(view)
				Pref.timing = now
			else:
				Pref.timing = now

	def highlight_occurences(self, view):
		regions = []
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
		if self.prev_regions != regions:
			view.erase_regions("WordHighlight")
			if regions:
				view.add_regions("WordHighlight", regions, Pref.color_scope_name, Pref.draw_outlined)
				
				#We read the length of get_regions because duplicate regions are
				#removed when they're added to the view.
				occurrences = len(view.get_regions("WordHighlight"))
				message = str(occurrences) + ' occurrence' + ('s' if occurrences != 1 else '') + ' of "' + string + '"'
				view.set_status("WordHighlight", message)
			else:
				view.erase_status("WordHighlight")
			self.prev_regions = regions
