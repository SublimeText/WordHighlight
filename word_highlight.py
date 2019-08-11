import re
import sys
import time
import threading

import sublime
import sublime_plugin

g_sleepEvent = threading.Event()
g_correct_view = None
g_is_already_running = False

commands_to_reset = ('single_selection', 'single_selection_first', 'single_selection_last')


class Pref:
    p = 'highlight_words_on_selection.'

    timing                         = time.time()
    enabled                        = True
    is_file_limit_reached          = False
    is_on_whole_word_mode          = False
    prev_selections                = None
    prev_regions                   = None

    select_next_word_last_word     = False
    select_previous_word_last_word = False

    select_word_undo               = []
    select_word_redo               = []
    select_next_word_skipped       = [ 0 ]
    select_previous_word_skipped   = [ sys.maxsize ]

    @classmethod
    def when_file_size_limit_search_this_num_of_characters(cls, settings):
        return int( settings.get( cls.p + 'when_file_size_limit_search_this_num_of_characters', 20000 ) )

    @classmethod
    def color_scope_name(cls, settings):
        return settings.get( cls.p + 'color_scope_name', 'comment' )

    @classmethod
    def case_sensitive(cls, settings):
        return ( not bool( settings.get( cls.p + 'case_sensitive', True ) ) ) * sublime.IGNORECASE

    @classmethod
    def draw_outlined(cls, settings):
        return bool( settings.get( cls.p + 'draw_outlined', True ) ) * sublime.DRAW_OUTLINED

    @classmethod
    def mark_occurrences_on_gutter(cls, settings):
        return bool( settings.get( cls.p + 'mark_occurrences_on_gutter', False ) )

    @classmethod
    def icon_type_on_gutter(cls, settings):
        return settings.get( cls.p + 'icon_type_on_gutter', 'dot' )

    @classmethod
    def when_selection_is_empty(cls, settings):
        return bool( settings.get( cls.p + 'when_selection_is_empty', False ) )

    @classmethod
    def only_whole_word_when_selection_is_empty(cls, settings):
        return bool( settings.get( cls.p + 'only_whole_word_when_selection_is_empty', False ) )

    @classmethod
    def word_under_cursor_when_selection_is_empty(cls, settings):
        return bool( settings.get( cls.p + 'word_under_cursor_when_selection_is_empty', False ) )

    @classmethod
    def non_word_characters(cls, settings):
        return bool( settings.get( cls.p + 'non_word_characters', False ) )

    @classmethod
    def file_size_limit(cls, settings):
        return int( settings.get( cls.p + 'file_size_limit', 4194304 ) )


def plugin_loaded():

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
            view.erase_regions( 'HighlightWordsOnSelection' )

        else:
            highlight_occurences(view)

    def description(self):
        return 'Disable' if Pref.enabled else 'Enable'


class SelectHighlightedWordsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        wh = self.view.get_regions( 'HighlightWordsOnSelection' )

        for w in wh:
            self.view.sel().add(w)


class SelectHighlightedNextWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if not view.has_non_empty_selection_region():
            Pref.is_on_whole_word_mode = True

        # print( 'selections', selections )
        if selections:
            word_regions = view.get_regions( 'HighlightWordsOnSelection' )

            if word_regions:
                # print( 'select_next_word_last_word', Pref.select_next_word_last_word, Pref.select_next_word_skipped )
                if Pref.select_next_word_last_word:
                    last_word = word_regions[0]
                    last_word_end = last_word.begin() - 1

                else:
                    last_word = selections[0]
                    last_word_end = last_word.end() - 1

                # print( 'last_word_end', last_word_end, view.substr( last_word ), 'select_next_word_skipped', Pref.select_next_word_skipped, 'word_regions', word_regions )
                for next_word in word_regions:

                    # print( 'next_word_end', next_word.end(), 'last_word_end', last_word_end, view.substr(next_word) )
                    if next_word.end() > last_word_end and next_word.end() > Pref.select_next_word_skipped[-1]:

                        if next_word in selections:
                            # print( 'skipping next_word', next_word )
                            continue

                        selections.add(next_word)
                        view.show(next_word)

                        Pref.select_word_undo.append( 'next' )
                        Pref.select_next_word_skipped.append( next_word.end() )
                        break;

                if next_word == word_regions[-1]:
                    # print( "Triggering FIX..." )
                    Pref.select_next_word_last_word = True

                    Pref.select_word_undo.append( 'next' )
                    Pref.select_next_word_skipped.append( word_regions[0].begin() )


class SelectHighlightedPreviousWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if not view.has_non_empty_selection_region():
            Pref.is_on_whole_word_mode = True

        # print( 'selections', selections )
        if selections:
            word_regions = view.get_regions( 'HighlightWordsOnSelection' )

            if word_regions:
                # print( 'select_previous_word_last_word', Pref.select_previous_word_last_word, Pref.select_previous_word_skipped )
                if Pref.select_previous_word_last_word:
                    first_word = word_regions[-1]
                    first_word_end = first_word.end() + 1

                else:
                    first_word = selections[0]
                    first_word_end = first_word.begin() + 1

                # print( 'first_word_end', first_word_end, view.substr( first_word ), 'select_previous_word_skipped', Pref.select_previous_word_skipped, 'word_regions', word_regions )
                for previous_word in reversed( word_regions ):

                    # print( 'previous_word_end', previous_word.end(), 'first_word_end', first_word_end, view.substr(previous_word) )
                    if previous_word.begin() < first_word_end and previous_word.begin() < Pref.select_previous_word_skipped[-1]:

                        if previous_word in selections:
                            # print( 'skipping first_word', first_word )
                            continue

                        selections.add(previous_word)
                        view.show(previous_word)

                        Pref.select_word_undo.append( 'previous' )
                        Pref.select_previous_word_skipped.append( previous_word.begin() )
                        break;

                if previous_word == word_regions[0]:
                    # print( "Triggering FIX..." )
                    Pref.select_previous_word_last_word = True

                    Pref.select_word_undo.append( 'previous' )
                    Pref.select_previous_word_skipped.append( word_regions[-1].end() )


class SelectHighlightedSkipNextWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if selections and len(selections) > 1:
            word_regions = view.get_regions( 'HighlightWordsOnSelection' )
            Pref.select_word_undo.append( 'next' )

            if selections[-1] == word_regions[-1]:
                Pref.select_next_word_skipped.append( 0 )

            else:
                Pref.select_next_word_skipped.append( selections[-1].end() )

            selections.subtract(selections[-1])
            view.run_command( 'select_highlighted_next_word' )


class SelectHighlightedSkipPreviousWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if selections and len(selections) > 1:
            word_regions = view.get_regions( 'HighlightWordsOnSelection' )
            Pref.select_word_undo.append( 'previous' )

            if selections[0] == word_regions[0]:
                Pref.select_previous_word_skipped.append( sys.maxsize )

            else:
                Pref.select_previous_word_skipped.append( selections[0].begin() )

            selections.subtract(selections[0])
            view.run_command( 'select_highlighted_previous_word' )


class WordHighlightListener(sublime_plugin.EventListener):

    def on_text_command(self, window, command_name, args):
        # print('command_name', command_name)

        if command_name == 'soft_undo':

            if Pref.select_word_undo:
                stack_type = Pref.select_word_undo.pop()

                if stack_type == 'next':
                    Pref.select_word_redo.append( (Pref.select_next_word_skipped.pop(), 'next') )

                else:
                    Pref.select_word_redo.append( (Pref.select_previous_word_skipped.pop(), 'previous') )

        elif command_name == 'soft_redo':

            if Pref.select_word_redo:
                elements = Pref.select_word_redo.pop()
                Pref.select_word_undo.append( elements[1] )

                if elements[1] == 'next':
                    Pref.select_next_word_skipped.append( elements[0] )

                else:
                    Pref.select_previous_word_skipped.append( elements[0] )

    def on_window_command(self, window, command_name, args):
        # print('command_name', command_name)

        if command_name in commands_to_reset:
            clear_line_skipping()

    def on_query_context(self, view, key, operator, operand, match_all):

        if key == 'is_highlight_words_on_selection_working':
            return not Pref.is_file_limit_reached and view.get_regions( 'HighlightWordsOnSelection' )

    def on_activated(self, view):
        # Pref.prev_selections = None

        if not view.is_loading():

            if not Pref.enabled:
                view.erase_regions( 'HighlightWordsOnSelection' )

    def on_selection_modified(self, view):
        # print('on_selection_modified', view.substr(sublime.Region(0, 10)))
        active_window = sublime.active_window()
        panel_has_focus = not view.file_name()

        # Multiple event hooks don’t work with clones
        # https://github.com/SublimeTextIssues/Core/issues/289
        is_widget = view.settings().get('is_widget')
        active_panel = active_window.active_panel()

        # print( "is_widget:", is_widget )
        # print( "panel_has_focus:", panel_has_focus )
        if not ( active_panel and panel_has_focus or is_widget ):
            view = active_window.active_view()

        if view and Pref.enabled and not is_widget:
            global g_correct_view
            g_correct_view = view

            # print( "view:", view )
            g_sleepEvent.set()


def clear_line_skipping():
    Pref.select_word_undo.clear()
    Pref.select_word_redo.clear()

    Pref.select_next_word_skipped = [ 0 ]
    Pref.select_previous_word_skipped = [ sys.maxsize ]

    Pref.is_on_whole_word_mode = False
    Pref.select_next_word_last_word = False
    Pref.select_previous_word_last_word = False


def highlight_occurences(view):
    settings = view.settings()

    # print( "view.has_non_empty_selection_region:", view.has_non_empty_selection_region() )
    if not view.has_non_empty_selection_region():
        clear_line_skipping()

        if not Pref.when_selection_is_empty(settings):
            view.erase_status( 'HighlightWordsOnSelection' )
            view.erase_regions( 'HighlightWordsOnSelection' )
            Pref.prev_regions = None
            Pref.prev_selections = None
            return

    prev_selections = str(view.sel())

    # print( "prev_selections:", prev_selections )
    if Pref.prev_selections == prev_selections:
        return

    else:
        Pref.prev_selections = prev_selections

    if view.size() <= Pref.file_size_limit(settings):
        limited_size = False

    else:
        limited_size = True

    # print( 'running', str(time.time()) )
    regions = []
    processedWords = []
    occurrencesMessage = []
    occurrencesCount = 0
    word_separators = settings.get( 'word_separators' )

    for sel in view.sel():

        if Pref.when_selection_is_empty(settings) and sel.empty():
            string = view.substr(view.word(sel)).strip()

            if string not in processedWords:
                processedWords.append(string)

                if string and all([not c in word_separators for c in string]):
                        regions = find_regions(view, regions, string, limited_size, True)

                if not Pref.word_under_cursor_when_selection_is_empty(settings):

                    for s in view.sel():
                        regions = [r for r in regions if not r.contains(s)]

        elif not sel.empty() and Pref.non_word_characters(settings):
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

                    if string and all([not c in word_separators for c in string]):
                            regions = find_regions(view, regions, string, limited_size, False)

        occurrences = len(regions)-occurrencesCount;

        if occurrences > 0:
            occurrencesMessage.append( '"' + string + '" ' + str(occurrences) + ' ' )
            occurrencesCount = occurrencesCount + occurrences

    if Pref.prev_regions != regions:
        view.erase_regions( 'HighlightWordsOnSelection' )

        if regions:
            view.add_regions( 'HighlightWordsOnSelection', regions, Pref.color_scope_name(settings), Pref.icon_type_on_gutter(settings) if  Pref.mark_occurrences_on_gutter(settings) else "", sublime.DRAW_NO_FILL if Pref.draw_outlined(settings) else 0)

        else:
            view.erase_status( 'HighlightWordsOnSelection' )

        Pref.prev_regions = regions


def find_regions(view, regions, string, limited_size, is_selection_empty):
    settings = view.settings()
    Pref.is_file_limit_reached = False

    # to to to too
    if Pref.non_word_characters(settings):
        if Pref.only_whole_word_when_selection_is_empty(settings) and is_selection_empty or Pref.is_on_whole_word_mode:
            search = r'\b' + escape_regex(string) + r'\b'

        else:
            search = escape_regex(string)

    else:
        # It seems as if \b doesn't pay attention to word_separators, but
        # \w does. Hence we use lookaround assertions instead of \b.
        if Pref.only_whole_word_when_selection_is_empty(settings) and is_selection_empty:
            search = r'\b(?<!\w)' + escape_regex(string) + r'(?!\w)\b'

        else:
            search = r'(?<!\w)' + escape_regex(string) + r'(?!\w)'

    if not limited_size:
        regions += view.find_all(search, Pref.case_sensitive(settings))

    else:
        chars = Pref.when_file_size_limit_search_this_num_of_characters(settings)
        visible_region = view.visible_region()

        begin = 0 if visible_region.begin() - chars < 0 else visible_region.begin() - chars
        end = visible_region.end() + chars
        from_point = begin

        while True:
            region = view.find(search, from_point)

            if region:
                regions.append(region)

                if region.end() > end:
                    Pref.is_file_limit_reached = True
                    break

                else:
                    from_point = region.end()

            else:
                break

    return regions

