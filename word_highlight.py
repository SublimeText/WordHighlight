import sublime
import sublime_plugin
import re

s = sublime.load_settings('Word Highlight.sublime-settings')

class Pref:
	def load(self):
		Pref.color_scope_name                  	= s.get('color_scope_name', "comment")
		Pref.draw_outlined                     	= bool(s.get('draw_outlined', True)) * sublime.DRAW_OUTLINED
		Pref.highlight_when_selection_is_empty 	= bool(s.get('highlight_when_selection_is_empty', True))

Pref().load();

s.add_on_change('color_scope_name',                  lambda:Pref().load())
s.add_on_change('draw_outlined',                     lambda:Pref().load())
s.add_on_change('highlight_when_selection_is_empty', lambda:Pref().load())

class WordHighlightListener(sublime_plugin.EventListener):
	prev_regions = []

	def on_activate(self, view):
		Pref.word_separators = view.settings().get('word_separators')

	def on_selection_modified(self, view):
		regions = []
		for sel in view.sel():
			if sel.empty() and Pref.highlight_when_selection_is_empty:
				string = view.substr(view.word(sel)).strip()
				if len(string) and all([not c in Pref.word_separators for c in string]):
					regions += view.find_all('(?<![\\w])'+re.escape(string)+'\\b')
			else:
				word = view.word(sel)
				if word.end() == sel.end() and word.begin() == sel.begin() :
					string = view.substr(word).strip()
					if len(string):
						regions += view.find_all('(?<![\\w])'+re.escape(string)+'\\b')
		if self.prev_regions != regions:
			view.erase_regions("WordHighlight")
			if len(regions):
				view.add_regions("WordHighlight", regions, Pref.color_scope_name, Pref.draw_outlined)
			self.prev_regions = regions
