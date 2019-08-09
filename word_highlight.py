import re
import sys
import time
import threading

import sublime
import sublime_plugin

Pref = {}
settings = {}
settings_base = {}

g_sleepEvent = threading.Event()
g_correct_view = None
g_is_already_running = False


def load_settings():
    global settings
    global settings_base
    settings = sublime.load_settings('HighlightWordsOnSelection.sublime-settings')

    if int(sublime.version()) >= 2174:
        settings_base = sublime.load_settings('Preferences.sublime-settings')

    else:
        settings_base = sublime.load_settings('Base File.sublime-settings')


def plugin_loaded():
    global Pref
    load_settings()

    class Pref:
        def load(self):
            Pref.color_scope_name                                    = settings.get('color_scope_name', "comment")
            Pref.case_sensitive                                      = (not bool(settings.get('case_sensitive', True))) * sublime.IGNORECASE
            Pref.draw_outlined                                       = bool(settings.get('draw_outlined', True)) * sublime.DRAW_OUTLINED
            Pref.mark_occurrences_on_gutter                          = bool(settings.get('mark_occurrences_on_gutter', False))
            Pref.icon_type_on_gutter                                 = settings.get("icon_type_on_gutter", "dot")
            Pref.highlight_when_selection_is_empty                   = bool(settings.get('highlight_when_selection_is_empty', False))
            Pref.highlight_only_whole_word_when_selection_is_empty   = bool(settings.get('highlight_only_whole_word_when_selection_is_empty', False))
            Pref.highlight_word_under_cursor_when_selection_is_empty = bool(settings.get('highlight_word_under_cursor_when_selection_is_empty', False))
            Pref.highlight_non_word_characters                       = bool(settings.get('highlight_non_word_characters', False))
            Pref.word_separators                                     = settings_base.get('word_separators')
            Pref.file_size_limit                                     = int(settings.get('file_size_limit', 4194304))
            Pref.when_file_size_limit_search_this_num_of_characters  = int(settings.get('when_file_size_limit_search_this_num_of_characters', 20000))
            Pref.timing                                              = time.time()
            Pref.enabled                                             = True
            Pref.prev_selections                                     = None
            Pref.prev_regions                                        = None
            Pref.select_next_word_skiped                             = 0

    Pref = Pref()
    Pref.load()

    settings.add_on_change('HighlightWordsOnSelectionBase', lambda: Pref.load())
    settings_base.add_on_change('HighlightWordsOnSelection', lambda: Pref.load())

    if not g_is_already_running:
        # unblocks any thread waiting in a g_sleepEvent.wait() call
        g_sleepEvent.set()

        # Wait last thread Preferences class to be unloaded
        sublime.set_timeout_async( configure_main_thread, 5000 )


def plugin_unloaded():
    global g_is_already_running
    g_is_already_running = False

    # unblocks any thread waiting in a g_sleepEvent.wait() call
    g_sleepEvent.set()

    settings_base.clear_on_change('HighlightWordsOnSelection')
    settings_base.clear_on_change('HighlightWordsOnSelectionBase')


def configure_main_thread():
    """
        break/interrupt a time.sleep() in python
        https://stackoverflow.com/questions/5114292/break-interrupt-a-time-sleep-in-python
    """
    global g_is_already_running
    g_is_already_running = True

    # Reset the internal flag to false. Subsequently, threads calling wait() will block until set()
    # is called to set the internal flag to true again.
    g_sleepEvent.clear()

    thread = threading.Thread( target=wh_loop )
    thread.start()


def wh_loop():
    global g_correct_view

    while True:
        # Stops the thread when the plugin is reloaded or unloaded
        if not g_is_already_running:
            break

        if g_correct_view:
            view = g_correct_view

            g_correct_view = None
            highlight_occurences( view )

        # Reset the internal flag to false. Subsequently, threads calling wait() will block until set()
        # is called to set the internal flag to true again.
        # https://stackoverflow.com/questions/5114292/break-interrupt-a-time-sleep-in-python
        g_sleepEvent.clear()
        g_sleepEvent.wait()


def escape_regex(str):
    # Sublime text chokes when regexes contain \', \<, \>, or \`.
    # Call re.escape to escape everything, and then unescape these four.
    str = re.escape(str)

    for c in "'<>`":
        str = str.replace('\\' + c, c)
    return str


class HighlightWordsOnSelectionEnabledCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        Pref.enabled = not Pref.enabled
        view = self.view

        if not Pref.enabled:
            view.erase_regions("HighlightWordsOnSelection")

        else:
            highlight_occurences(view)

    def description(self):
        return 'Disable' if Pref.enabled else 'Enable'


class SelectHighlightedWordsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        wh = self.view.get_regions("HighlightWordsOnSelection")

        for w in wh:
            self.view.sel().add(w)


class SelectHighlightedNextWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sel = [s for s in self.view.sel()]
        sel.reverse()

        if sel:
            word = sel[0]
            wh = self.view.get_regions("HighlightWordsOnSelection")

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


class WordHighlightListener(sublime_plugin.EventListener):
    def on_activated(self, view):
        Pref.prev_selections = None
        Pref.select_next_word_skiped = 0

        if not view.is_loading():
            Pref.word_separators = view.settings().get('word_separators') or settings_base.get('word_separators')

            if not Pref.enabled:
                view.erase_regions("HighlightWordsOnSelection")

    def on_selection_modified(self, view):
        # print('on_selection_modified', view.substr(sublime.Region(0, 10)))
        active_window = sublime.active_window()
        panel_has_focus = not view.file_name()

        is_widget = view.settings().get('is_widget')
        active_panel = active_window.active_panel()

        # print( "is_widget:", is_widget )
        # print( "panel_has_focus:", panel_has_focus )
        if active_panel and panel_has_focus or is_widget:
            # print( '1' )
            correct_view = view

        else:
            # print( '2' )
            correct_view = active_window.active_view()

        if correct_view and Pref.enabled and not is_widget:
            global g_correct_view
            g_correct_view = correct_view

            # print( "correct_view:", correct_view )
            g_sleepEvent.set()


def highlight_occurences(view):
    # print( "view.has_non_empty_selection_region:", view.has_non_empty_selection_region() )
    if not Pref.highlight_when_selection_is_empty and not view.has_non_empty_selection_region():
        view.erase_status("HighlightWordsOnSelection")
        view.erase_regions("HighlightWordsOnSelection")
        Pref.prev_regions = None
        Pref.prev_selections = None
        return

    # todo: The list cast below can go away when Sublime 3's Selection class implements __str__
    prev_selections = str(list(view.sel()))

    # print( "prev_selections:", prev_selections )
    if Pref.prev_selections == prev_selections:
        return

    else:
        Pref.prev_selections = prev_selections

    if view.size() <= Pref.file_size_limit:
        limited_size = False

    else:
        limited_size = True

    # print( 'running'+ str(time.time()) )
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
                        regions = find_regions(view, regions, string, limited_size, True)

                if not Pref.highlight_word_under_cursor_when_selection_is_empty:

                    for s in view.sel():
                        regions = [r for r in regions if not r.contains(s)]

        elif not sel.empty() and Pref.highlight_non_word_characters:
            string = view.substr(sel)

            if string and string not in processedWords:
                processedWords.append(string)
                regions = find_regions(view, regions, string, limited_size, False)

        elif not sel.empty():
            word = view.word(sel)

            if word.end() == sel.end() and word.begin() == sel.begin():
                string = view.substr(word).strip()

                if string not in processedWords:
                    processedWords.append(string)

                    if string and all([not c in Pref.word_separators for c in string]):
                            regions = find_regions(view, regions, string, limited_size, False)

        occurrences = len(regions)-occurrencesCount;

        if occurrences > 0:
            occurrencesMessage.append('"' + string + '" '+str(occurrences) +' ')
            occurrencesCount = occurrencesCount + occurrences

    if Pref.prev_regions != regions:
        view.erase_regions("HighlightWordsOnSelection")

        if regions:
            view.add_regions("HighlightWordsOnSelection", regions, Pref.color_scope_name, Pref.icon_type_on_gutter if Pref.mark_occurrences_on_gutter else "", sublime.DRAW_NO_FILL if Pref.draw_outlined else 0)

        else:
            view.erase_status("HighlightWordsOnSelection")

        Pref.prev_regions = regions


def find_regions(view, regions, string, limited_size, is_selection_empty):
    # to to to too
    if Pref.highlight_non_word_characters:
        if Pref.highlight_only_whole_word_when_selection_is_empty and is_selection_empty:
            search = r'\b'+escape_regex(string)+r'\b'

        else:
            search = escape_regex(string)

    else:
        # It seems as if \b doesn't pay attention to word_separators, but
        # \w does. Hence we use lookaround assertions instead of \b.
        if Pref.highlight_only_whole_word_when_selection_is_empty and is_selection_empty:
            search = r'\b(?<!\w)'+escape_regex(string)+r'(?!\w)\b'

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

