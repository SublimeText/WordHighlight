import re
import sys
import time
import threading

import sublime
import sublime_plugin

g_sleepEvent = threading.Event()
g_is_already_running = False

g_regionkey = "HighlightWordsOnSelection"
g_statusbarkey = "HighlightWordsOnSelection"


class Pref:
    p = 'highlight_words_on_selection.'

    timing                         = time.time()
    enabled                        = True
    is_file_limit_reached          = False
    is_on_word_selection_mode      = False
    prev_selections                = None
    prev_regions                   = None

    correct_view                   = None
    region_borders                 = None
    selected_first_word            = None
    selected_last_word             = []

    has_selected_new_word          = False
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
    def enable_find_under_expand_bug_fixes(cls, settings):
        return bool( settings.get( cls.p + 'enable_find_under_expand_bug_fixes', False ) )

    @classmethod
    def copy_selected_text_into_find_panel(cls, settings):
        return bool( settings.get( cls.p + 'copy_selected_text_into_find_panel', True ) )

    @classmethod
    def blink_selection_on_single_selection(cls, settings):
        return bool( settings.get( cls.p + 'blink_selection_on_single_selection', True ) )

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

    for window in sublime.windows():
        for view in window.views():
            view.erase_status( g_statusbarkey )
            view.erase_regions( g_regionkey )


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

    while True:
        # Stops the thread when the plugin is reloaded or unloaded
        if not g_is_already_running:
            break

        if Pref.correct_view:
            view = Pref.correct_view

            Pref.correct_view = None
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


def force_focus(view, region_borders):
    window = view.window()
    window.focus_view( view )
    view.show( region_borders )


def fix_selection_aligment(selections, region_borders):

    if selections:
        last_selection = None

        for selection in sorted( selections, key=lambda item: item.begin() ):
            # print('selection.begin', selection.begin())

            if selection.begin() > region_borders.begin():

                if last_selection is None:
                    last_selection = selection
                break

            last_selection = selection

        return last_selection


class WordHighlightOnSelectionSingleSelectionBlinkerCommand(sublime_plugin.TextCommand):

    def run(self, edit, message):
        view = self.view
        selections = view.sel()
        settings = view.settings()
        Pref.region_borders = fix_selection_aligment( selections, Pref.region_borders )

        def run_blinking_focus():
            force_focus( view, Pref.region_borders )
            view.run_command( "word_highlight_on_selection_single_selection_blinker_helper" )

        selections.clear()
        sublime.status_message( "Selection set to %s %s" % ( message, view.substr( Pref.region_borders )[:100] ) )

        # view.run_command( "move", {"by": "characters", "forward": False} )
        # print( "SingleSelectionLast, Selecting last:", Pref.region_borders )
        if Pref.blink_selection_on_single_selection( settings ):
            selections.add( Pref.region_borders.end() )
            sublime.set_timeout( run_blinking_focus, 250 )
            force_focus( view, Pref.region_borders )

        else:
            selections.add( Pref.region_borders )
            force_focus( view, Pref.region_borders )


class WordHighlightOnSelectionSingleSelectionBlinkerHelperCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        # print( 'Calling Selection Last Helper... ', Pref.region_borders )
        view = self.view
        selections = view.sel()

        selections.clear()
        selections.add( Pref.region_borders )
        Pref.region_borders = None


class HighlightWordsOnSelectionEnabledCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        Pref.enabled = not Pref.enabled
        view = self.view

        if not Pref.enabled:
            view.erase_regions( g_regionkey )

        else:
            highlight_occurences(view)

    def description(self):
        return 'Disable' if Pref.enabled else 'Enable'


class SelectHighlightedWordsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        wh = view.get_regions( g_regionkey )
        selections = view.sel()

        for w in wh:
            selections.add(w)


def show_status_bar(view, selections, word_regions):
    view.set_status(
            g_statusbarkey, "Selected %s of %s%s occurrences" % (
                len( selections ),
                "approximately ~" if Pref.is_file_limit_reached else "",
                len( word_regions )
            )
        )


class SelectHighlightedNextWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        sublime.set_timeout( lambda: view.run_command( 'select_highlighted_next_word_bug_fixer' ), 0 )


class SelectHighlightedNextWordBugFixerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if not view.has_non_empty_selection_region():
            Pref.is_on_word_selection_mode = True

        # print( 'selections', [s for s in selections] )
        if selections:
            Pref.has_selected_new_word = False
            word_regions = view.get_regions( g_regionkey )

            if word_regions:
                settings = view.settings()
                copy_selected_text_into_find_panel = Pref.copy_selected_text_into_find_panel( settings )
                next_word = run_next_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

                if len( word_regions ) == len( selections ):
                    sublime.status_message( "Selected all occurrences of the word '%s' on the file!" % view.substr( next_word )[:100] )

                elif next_word == word_regions[-1]:
                        sublime.status_message( "Reached the last word '%s' on the file!" % view.substr( next_word )[:100] )
                        Pref.select_next_word_last_word = True

                        Pref.select_word_undo.append( 'next' )
                        Pref.select_next_word_skipped.append( word_regions[0].begin() )

                        if not Pref.has_selected_new_word:
                            run_next_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

                show_status_bar( view, selections, word_regions )


def run_next_selection_search(view, word_regions, selections, copy_selected_text_into_find_panel):
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

            if Pref.selected_first_word is None:
                Pref.selected_first_word = next_word

                if copy_selected_text_into_find_panel:
                    view.window().run_command( "fixed_toggle_find_panel", {
                            "command": "insert",
                            "skip": True,
                            "args": { "characters": view.substr( next_word ) }
                            } )

            if not next_word.empty() and selections.contains( next_word ):
                # print( 'skipping next_word', next_word )
                continue

            selections.add( next_word )
            view.show( next_word )

            Pref.select_word_undo.append( 'next' )
            Pref.select_next_word_skipped.append( next_word.end() )

            Pref.has_selected_new_word = True
            Pref.selected_last_word.append( next_word )
            break;

    return next_word


class SelectHighlightedPreviousWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        sublime.set_timeout( lambda: view.run_command( 'select_highlighted_previous_word_bug_fixer' ), 0 )


class SelectHighlightedPreviousWordBugFixerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if not view.has_non_empty_selection_region():
            Pref.is_on_word_selection_mode = True

        # print( 'selections', [s for s in selections] )
        if selections:
            Pref.has_selected_new_word = False
            word_regions = view.get_regions( g_regionkey )

            if word_regions:
                settings = view.settings()
                copy_selected_text_into_find_panel = Pref.copy_selected_text_into_find_panel( settings )
                previous_word = run_previous_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

                if len( word_regions ) == len( selections ):
                    sublime.status_message( "Selected all occurrences of the word '%s' on the file!" % view.substr( previous_word )[:100] )

                elif previous_word == word_regions[0]:
                        sublime.status_message( "Reached the first word '%s' on the file!" % view.substr( previous_word )[:100] )
                        Pref.select_previous_word_last_word = True

                        Pref.select_word_undo.append( 'previous' )
                        Pref.select_previous_word_skipped.append( word_regions[-1].end() )

                        if not Pref.has_selected_new_word:
                            run_previous_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

                show_status_bar( view, selections, word_regions )


def run_previous_selection_search(view, word_regions, selections, copy_selected_text_into_find_panel):
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

            if Pref.selected_first_word is None:
                Pref.selected_first_word = previous_word

                if copy_selected_text_into_find_panel:
                    view.window().run_command( "fixed_toggle_find_panel", {
                            "command": "insert",
                            "skip": True,
                            "args": { "characters": view.substr( previous_word ) }
                            } )

            if not previous_word.empty() and selections.contains( previous_word ):
                # print( 'skipping previous_word', previous_word )
                continue

            selections.add( previous_word )
            view.show( previous_word )

            Pref.select_word_undo.append( 'previous' )
            Pref.select_previous_word_skipped.append( previous_word.begin() )

            Pref.has_selected_new_word = True
            Pref.selected_last_word.append( previous_word )
            break;

    return previous_word


class SelectHighlightedSkipNextWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if selections:
            word_regions = view.get_regions( g_regionkey )
            Pref.select_word_undo.append( 'next' )

            if selections[-1] == word_regions[-1]:
                Pref.select_next_word_skipped.append( 0 )

            else:
                Pref.select_next_word_skipped.append( selections[-1].end() )

            if len( Pref.select_next_word_skipped ) > 1 and len( selections ) > 1:
                selections.subtract( selections[-1] )
                view.run_command( 'select_highlighted_next_word' )

            else:
                view.run_command( 'select_highlighted_next_word' )
                sublime.set_timeout( lambda: view.run_command( 'select_highlighted_skip_next_word_helper', { "counter": 1 } ) )


class SelectHighlightedSkipNextWordHelperCommand(sublime_plugin.TextCommand):
    def run(self, edit, counter):
        counter -= 1
        view = self.view
        selections = view.sel()

        if len( selections ) < 2:
            if counter < 0: return
            view.run_command( 'select_highlighted_next_word' )
            sublime.set_timeout( lambda: view.run_command( 'select_highlighted_skip_next_word_helper', { "counter": counter } ) )

        else:
            selections.subtract( selections[0] )


class SelectHighlightedSkipPreviousWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()

        if selections:
            word_regions = view.get_regions( g_regionkey )
            Pref.select_word_undo.append( 'previous' )

            if selections[0] == word_regions[0]:
                Pref.select_previous_word_skipped.append( sys.maxsize )

            else:
                Pref.select_previous_word_skipped.append( selections[0].begin() )

            if len( Pref.select_previous_word_skipped ) > 1 and len( selections ) > 1:
                selections.subtract( selections[0] )
                view.run_command( 'select_highlighted_previous_word' )

            else:
                view.run_command( 'select_highlighted_previous_word' )
                sublime.set_timeout( lambda: view.run_command( 'select_highlighted_skip_previous_word_helper', { "counter": 1 } ) )


class SelectHighlightedSkipPreviousWordHelperCommand(sublime_plugin.TextCommand):
    def run(self, edit, counter):
        counter -= 1
        view = self.view
        selections = view.sel()

        if len( selections ) < 2:
            if counter < 0: return
            view.run_command( 'select_highlighted_previous_word' )
            sublime.set_timeout( lambda: view.run_command( 'select_highlighted_skip_previous_word_helper', { "counter": counter } ) )

        else:
            selections.subtract( selections[-1] )


class WordHighlightListener(sublime_plugin.EventListener):

    def on_text_command(self, view, command_name, args):
        # print('command_name', command_name, args)

        if command_name == 'soft_undo':

            if Pref.select_word_undo:
                stack_type = Pref.select_word_undo.pop()
                selected_last_word = Pref.selected_last_word.pop() if Pref.selected_last_word else None

                if Pref.selected_last_word:
                    view.show( Pref.selected_last_word[-1] )

                if stack_type == 'next':
                    Pref.select_word_redo.append( (Pref.select_next_word_skipped.pop(), 'next', selected_last_word) )

                else:
                    Pref.select_word_redo.append( (Pref.select_previous_word_skipped.pop(), 'previous', selected_last_word) )

        elif command_name == 'soft_redo':

            if Pref.select_word_redo:
                elements = Pref.select_word_redo.pop()
                skipped_word = elements[0]
                stack_type = elements[1]

                selected_last_word = elements[2]
                Pref.select_word_undo.append( stack_type )

                if selected_last_word:
                    Pref.selected_last_word.append( selected_last_word )
                    view.show( selected_last_word )

                if stack_type == 'next':
                    Pref.select_next_word_skipped.append( skipped_word )

                else:
                    Pref.select_previous_word_skipped.append( skipped_word )

        elif command_name == 'single_selection':
            clear_line_skipping( view, keep_whole_word_state=True )

        elif command_name == 'single_selection_first':

            if Pref.enable_find_under_expand_bug_fixes( view.settings() ) and Pref.selected_first_word is not None:
                Pref.region_borders = Pref.selected_first_word

                clear_line_skipping( view, keep_whole_word_state=True )
                return ('word_highlight_on_selection_single_selection_blinker', { "message": "FIRST" })

            clear_line_skipping( view, keep_whole_word_state=True )

        elif command_name == 'single_selection_last':

            if Pref.enable_find_under_expand_bug_fixes( view.settings() ) and Pref.selected_last_word:
                Pref.region_borders = Pref.selected_last_word[-1]

                clear_line_skipping( view, keep_whole_word_state=True )
                return ('word_highlight_on_selection_single_selection_blinker', { "message": "LAST" })

            clear_line_skipping( view, keep_whole_word_state=True )

        elif command_name == 'drag_select':

            if not ( 'additive' in args or 'subtractive' in args ):
                clear_line_skipping( view )

        elif command_name == 'move':
            clear_line_skipping( view )

    def on_query_context(self, view, key, operator, operand, match_all):

        if key == 'is_highlight_words_on_selection_working':
            return not Pref.is_file_limit_reached and view.get_regions( g_regionkey )

    def on_activated(self, view):
        # Pref.prev_selections = None

        if not view.is_loading():

            if not Pref.enabled:
                view.erase_regions( g_regionkey )

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
            Pref.correct_view = view
            g_sleepEvent.set()


def clear_line_skipping(view, keep_whole_word_state=False):
    # print('Reseting... keep_whole_word_state', keep_whole_word_state, Pref.region_borders)

    if ( not keep_whole_word_state or not view.has_non_empty_selection_region() ) and not Pref.region_borders:
        Pref.is_on_word_selection_mode = False

    # to to to too
    Pref.select_word_undo.clear()
    Pref.select_word_redo.clear()

    Pref.selected_first_word = None
    Pref.selected_last_word.clear()

    Pref.select_next_word_skipped = [ 0 ]
    Pref.select_previous_word_skipped = [ sys.maxsize ]

    Pref.select_next_word_last_word = False
    Pref.select_previous_word_last_word = False


def highlight_occurences(view):
    settings = view.settings()

    # print( "view.has_non_empty_selection_region:", view.has_non_empty_selection_region() )
    if not view.has_non_empty_selection_region():
        clear_line_skipping( view )

        if not Pref.when_selection_is_empty(settings):
            view.erase_status( g_statusbarkey )
            view.erase_regions( g_regionkey )
            Pref.prev_regions = None
            Pref.prev_selections = None
            return

    selections = view.sel()
    prev_selections = str( selections )

    # print( "prev_selections:", prev_selections )
    if Pref.prev_selections == prev_selections:
        return

    else:
        Pref.prev_selections = prev_selections

    if view.size() <= Pref.file_size_limit(settings):
        Pref.is_file_limit_reached = False

    else:
        Pref.is_file_limit_reached = True

    # print( 'running', str(time.time()) )
    word_regions = []
    processedWords = []
    occurrencesMessage = []
    occurrencesCount = 0
    word_separators = settings.get( 'word_separators' )

    for sel in selections:

        if sel.empty():

            if Pref.when_selection_is_empty(settings):
                string = view.substr(view.word(sel)).strip()

                if string not in processedWords:
                    processedWords.append(string)
                    is_word = all([not c in word_separators for c in string])

                    if string and is_word:
                        word_regions = find_regions(view, word_regions, string, True)

                    if not Pref.word_under_cursor_when_selection_is_empty(settings):

                        for s in selections:
                            word_regions = [r for r in word_regions if not r.contains(s)]

        elif Pref.non_word_characters(settings):
            string = view.substr(sel)

            if string and string not in processedWords:
                processedWords.append(string)
                word_regions = find_regions(view, word_regions, string, False)

        else:
            word = view.word(sel)

            if word.end() == sel.end() and word.begin() == sel.begin():
                string = view.substr(word).strip()

                if string not in processedWords:
                    processedWords.append(string)

                    if string and all([not c in word_separators for c in string]):
                            word_regions = find_regions(view, word_regions, string, False)

        occurrences = len(word_regions)-occurrencesCount;

        if occurrences > 0:
            occurrencesMessage.append( '"' + string + '" ' + str(occurrences) + ' ' )
            occurrencesCount = occurrencesCount + occurrences

    if Pref.prev_regions != word_regions:
        Pref.prev_regions = word_regions
        view.erase_regions( 'HighlightWordsOnSelection' )

        if word_regions:
            view.add_regions( 'HighlightWordsOnSelection', word_regions,
                    Pref.color_scope_name( settings ), Pref.icon_type_on_gutter( settings )
                            if Pref.mark_occurrences_on_gutter( settings ) else
                    "", sublime.DRAW_NO_FILL if Pref.draw_outlined( settings ) else 0 )

            show_status_bar( view, selections, word_regions )

        else:
            view.erase_status( g_statusbarkey )

    elif not word_regions:
        view.erase_status( g_statusbarkey )
        view.erase_regions( g_regionkey )


def find_regions(view, word_regions, string, is_selection_empty):
    settings = view.settings()

    # to to to too
    if Pref.non_word_characters(settings):
        if Pref.is_on_word_selection_mode or \
                Pref.only_whole_word_when_selection_is_empty(settings) and is_selection_empty:
            search = r'\b' + escape_regex(string) + r'\b'

        else:
            search = escape_regex(string)

    else:
        # It seems as if \b doesn't pay attention to word_separators, but
        # \w does. Hence we use lookaround assertions instead of \b.
        if Pref.is_on_word_selection_mode or \
                Pref.only_whole_word_when_selection_is_empty(settings) and is_selection_empty:
            search = r'\b(?<!\w)' + escape_regex(string) + r'(?!\w)\b'

        else:
            search = r'(?<!\w)' + escape_regex(string) + r'(?!\w)'

    if not Pref.is_file_limit_reached:
        word_regions += view.find_all(search, Pref.case_sensitive(settings))

    else:
        chars = Pref.when_file_size_limit_search_this_num_of_characters(settings)
        visible_region = view.visible_region()

        begin = 0 if visible_region.begin() - chars < 0 else visible_region.begin() - chars
        end = visible_region.end() + chars
        from_point = begin

        while True:
            region = view.find(search, from_point)

            if region:
                word_regions.append(region)

                if region.end() > end:
                    break

                else:
                    from_point = region.end()

            else:
                break

    return word_regions

