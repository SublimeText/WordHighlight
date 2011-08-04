"""
DRAW OUTLINED
	"draw_outlined" : true
		This makes the highlights be drawn as outlines instead of as filled
		highlights.

HIGHLIGHT WORDS WHEN SELECTION IS EMPTY
	"highlight_when_selection_is_empty" : true
		This makes words highlight when the insertion point is inside of them but
		when they're not actually selected.

COLOR OPTIONS
	"color_scope_name" : "wordhighlight"
		Normally the color of the highlights is the same as the color of comments in
		your code. If you'd like to customize the color, add the below to your color
		scheme file and change EDF2E9 to whatever color you want, then change
		color_scope_name to the scope name in the block you added.
---ADD TEXT BELOW THIS LINE TO YOUR COLOR SCHEME FILE---
		<dict>
				<key>name</key>
				<string>WordHighlight</string>
				<key>scope</key>
				<string>wordhighlight</string>
				<key>settings</key>
				<dict>
					<key>foreground</key>
					<string>#EDF2E9</string>
			 </dict>
		</dict>
---ADD TEXT ABOVE THIS LINE TO YOUR COLOR SCHEME FILE---
"""

import sublime
import sublime_plugin

DEFAULT_COLOR_SCOPE_NAME = "comment"

def regex_escape(string):
	outstring = ""
	for c in string:
		if c != '\\':
			outstring += '['+c+']'
		else:
			outstring += '\\'
	return outstring

class WordHighlightListener(sublime_plugin.EventListener):
	def on_selection_modified(self,view):
		word_separators = view.settings().get('word_separators')
		
		settings = sublime.load_settings('Word Highlight.sublime-settings')
		color_scope_name = settings.get('color_scope_name', DEFAULT_COLOR_SCOPE_NAME)
		draw_outlined = bool(settings.get('draw_outlined')) * sublime.DRAW_OUTLINED
		
		regions = []
		for sel in view.sel():
			#If we directly compare sel and view.word(sel), then it compares their
			#a and b values rather than their begin() and end() values. This means
			#that a leftward selection (with a > b) will never match the view.word()
			#of itself.
			#As a workaround, we compare the lengths instead.
			if len(sel) < 200 and len(sel) == len(view.word(sel)):
				string = view.substr(sel).strip()
				if len(string):
					regions += view.find_all('\\b'+regex_escape(string)+'\\b')
			elif len(sel) == 0 and bool(settings.get('highlight_when_selection_is_empty')):
				string = view.substr(view.word(sel)).strip()
				if len(string) and all([not c in word_separators for c in string]):
					regions += view.find_all('\\b'+regex_escape(string)+'\\b')
		view.add_regions("WordHighlight", regions, color_scope_name, draw_outlined)
