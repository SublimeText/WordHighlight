import sublime
import sublime_plugin
import re
import time

settings = sublime.load_settings('Word Highlight.sublime-settings')

class Pref:
	def load(self):
		Pref.color_scope_name                  	= settings.get('color_scope_name', "comment")
		Pref.draw_outlined                     	= bool(settings.get('draw_outlined', True)) * sublime.DRAW_OUTLINED
		Pref.highlight_when_selection_is_empty 	= bool(settings.get('highlight_when_selection_is_empty', True))
		Pref.word_separators										= []
		Pref.timing 														= time.time()

Pref().load();

settings.add_on_change('color_scope_name',                  lambda:Pref().load())
settings.add_on_change('draw_outlined',                     lambda:Pref().load())
settings.add_on_change('highlight_when_selection_is_empty', lambda:Pref().load())

class WordHighlightListener(sublime_plugin.EventListener):
	prev_regions = []

	def on_activate(self, view):
		Pref.word_separators = view.settings().get('word_separators')

	def on_selection_modified(self, view):
		now = time.time()
		if now - Pref.timing > 0.05:
			# print ' same thread'
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
			self.prev_regions = regions