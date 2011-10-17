import sublime
import sublime_plugin
from threading import Timer

DEFAULT_COLOR_SCOPE_NAME = "comment"

settings = sublime.load_settings('Word Highlight.sublime-settings')

def regex_escape(string):
	outstring = ""
	for c in string:
		if c != '\\':
			outstring += '['+c+']'
		else:
			outstring += '\\'
	return outstring

def delayed(seconds):
	def decorator(f):
		def wrapper(*args, **kargs):
			if wrapper.timer:
				wrapper.timer.cancel()
				wrapper.timer = None
			wrapper.timer = Timer(seconds, f, args, kargs)
			wrapper.timer.start()
		wrapper.timer = None
		return wrapper
	return decorator

class WordHighlightListener(sublime_plugin.EventListener):
	# This may need adjusting, or may be taken out altogether (once the selection bug is gone)
	@delayed(0.25)
	def pend_highlight_occurences(self,view):
		# Would execute highlight_occurences code directly, but it is not allowed
		# from thread (which we are currently in) under Windows OS. Therefore, queue.
		sublime.set_timeout(lambda: self.highlight_occurences(view), 0)

	def highlight_occurences(self,view):
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
					regions += view.find_all('(?<![\\w])' + regex_escape(string)+'\\b')
			elif len(sel) == 0 and bool(settings.get('highlight_when_selection_is_empty')):
				word_separators = view.settings().get('word_separators')
				string = view.substr(view.word(sel)).strip()
				if len(string) and all([not c in word_separators for c in string]):
					regions += view.find_all('(?<![\\w])'+regex_escape(string)+'\\b')
		if self.prev_regions != regions:
			color_scope_name = settings.get('color_scope_name', DEFAULT_COLOR_SCOPE_NAME)
			draw_outlined = bool(settings.get('draw_outlined')) * sublime.DRAW_OUTLINED
			view.add_regions("WordHighlight", regions, color_scope_name, draw_outlined)
			self.prev_regions = regions
	prev_regions = []

	def on_selection_modified(self,view):
		self.pend_highlight_occurences(view)
