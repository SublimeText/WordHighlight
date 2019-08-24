import re
import sys
import time
import threading
import datetime

from collections import deque

import sublime
import sublime_plugin

warning = print
CLEAR_CURSORS_CARETS_BLINKING = 300

debug_stack = print
debug_stack = lambda *args: None

g_sleepEvent = threading.Event()
g_is_already_running = False

g_regionkey = "HighlightWordsOnSelection"
g_statusbarkey = "HighlightWordsOnSelection"
g_view_selections = {}

try:
    from FixedToggleFindPanel.fixed_toggle_find_panel import is_panel_focused

except ImportError as error:
    print( 'WordHighlightOnSelection Error: Could not import the FixedToggleFindPanel package!', error )

    def is_panel_focused():
        return False


class get_selections_stack(object):
    def __repr__(self):
        state = State()

        return "select_word_undo_stack %s %s select_word_redo_stack %s %s %s" % (
                state.select_word_undo_stack, state.select_next_word_skipped,
                state.select_word_redo_stack, state.select_previous_word_skipped,
                state.is_file_limit_reached,
            )

class timestamp(object):
    def __repr__(self):
        return "%s" % (
                datetime.datetime.now(),
            )

# Allows to pass get_selections_stack as a function parameter without evaluating/creating its string!
timestamp = timestamp()
get_selections_stack = get_selections_stack()


def State(view=None):
    view = view or Pref.active_view or sublime.active_window().active_view()
    Pref.active_view = view
    return g_view_selections.setdefault( view.id(), Pref() )


class Pref:
    p = 'highlight_words_on_selection.'
    enabled = True
    active_view = None
    correct_view = None

    prev_regions = None
    prev_selections = None

    def __init__(self):
        self.blink_region = None
        self.is_file_limit_reached = False
        self.is_on_word_selection_mode = False

        self.has_selected_new_word = False
        self.select_next_word_from_beginning  = False
        self.select_previous_word_from_bottom = False

        self.selected_first_word = None
        self.selected_last_word = deque()

        self.select_word_undo_stack = []
        self.select_word_redo_stack = []
        self.select_next_word_skipped = [ 0 ]
        self.select_previous_word_skipped = [ sys.maxsize ]

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
    def always_enable_selection_regions(cls, settings):
        return bool( settings.get( cls.p + 'always_enable_selection_regions', False ) )

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

    if is_panel_focused():
        window = view.window() or sublime.active_window()
        view = window.active_view()

    view.set_status(
            g_statusbarkey, "Selected %s of %s%s occurrences" % (
                len( selections ),
                "~" if State().is_file_limit_reached else "",
                len( word_regions )
            )
        )


class SelectHighlightedNextWordCommand(sublime_plugin.TextCommand):
    """ https://github.com/SublimeTextIssues/Core/issues/2924 """
    def run(self, edit):
        view = self.view
        sublime.set_timeout( lambda: view.run_command( 'select_highlighted_next_word_bug_fixer' ), 0 )


class SelectHighlightedNextWordBugFixerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()
        select_highlighted_next_word_bug_fixer( view, selections )


def select_highlighted_next_word_bug_fixer(view, selections):
    state = State( view )

    if not view.has_non_empty_selection_region():
        state.is_on_word_selection_mode = True

    # print( 'selections', [s for s in selections] )
    if selections:
        state.has_selected_new_word = False
        word_regions = view.get_regions( g_regionkey )

        if word_regions:
            settings = view.settings()
            copy_selected_text_into_find_panel = state.copy_selected_text_into_find_panel( settings )
            next_word = run_next_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

            if len( word_regions ) == len( selections ):
                sublime.status_message( "Selected all occurrences of the word '%s' on the file!" % view.substr( next_word )[:100] )

            elif next_word == word_regions[-1]:
                    sublime.status_message( "Reached the last word '%s' on the file!" % view.substr( next_word )[:100] )
                    state.select_next_word_from_beginning = True

                    state.select_word_undo_stack.append( 'fake_next' )
                    state.select_next_word_skipped.append( word_regions[0].begin() )

                    if not state.has_selected_new_word:
                        run_next_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

            show_status_bar( view, selections, word_regions )


def run_next_selection_search(view, word_regions, selections, copy_selected_text_into_find_panel):
    state = State( view )

    # print( 'select_next_word_from_beginning', state.select_next_word_from_beginning, state.select_next_word_skipped )
    if state.select_next_word_from_beginning:
        last_word = word_regions[0]
        last_word_end = last_word.begin() - 1

    else:
        last_word = state.selected_last_word[-1] if state.selected_last_word else selections[-1]
        last_word_end = last_word.end() - 1

    # print( 'last_word_end', last_word_end, view.substr( last_word ), 'select_next_word_skipped', state.select_next_word_skipped, 'word_regions', word_regions )
    for next_word in word_regions:

        # print( 'next_word_end', next_word.end(), 'last_word_end', last_word_end, view.substr(next_word) )
        if next_word.end() > last_word_end and next_word.end() > state.select_next_word_skipped[-1]:

            if state.selected_first_word is None:
                state.selected_first_word = next_word

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

            state.select_word_redo_stack.clear()
            state.select_word_undo_stack.append( 'next' )
            state.select_next_word_skipped.append( next_word.end() )

            state.has_selected_new_word = True
            state.selected_last_word.append( next_word )
            break;

    debug_stack( timestamp, 'next_word', get_selections_stack )
    return next_word


class SelectHighlightedSkipNextWordCommand(sublime_plugin.TextCommand):
    """ https://github.com/SublimeTextIssues/Core/issues/2924 """
    def run(self, edit):
        view = self.view
        sublime.set_timeout( lambda: view.run_command( 'select_highlighted_skip_next_word_bug_fixer' ), 0 )


class SelectHighlightedSkipNextWordBugFixerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()
        word_regions = view.get_regions( g_regionkey )
        state = State( view )

        if selections and ( len( selections ) != len( word_regions ) or state.is_file_limit_reached ):

            if len( state.select_next_word_skipped ) > 1 and len( selections ) > 1:
                unselect = state.selected_last_word.pop() if state.selected_last_word else selections[-1]

                selections.subtract( unselect )
                select_highlighted_next_word_bug_fixer( view, selections )

            else:
                select_highlighted_next_word_bug_fixer( view, selections )
                select_highlighted_skip_next_word_helper( view, selections, 1 )

        else:
            debug_stack( timestamp, 'skip_next', get_selections_stack )


def select_highlighted_skip_next_word_helper(view, selections, counter):
    counter -= 1

    if len( selections ) < 2:
        if counter < 0: return

        select_highlighted_next_word_bug_fixer( view, selections )
        select_highlighted_skip_next_word_helper( view, selections, counter )

    else:
        debug_stack( timestamp, 'skip_next', get_selections_stack )
        state = State( view )

        unselect = state.selected_last_word.popleft() if state.selected_last_word else selections[0]
        selections.subtract( unselect )


class SelectHighlightedPreviousWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view

        # https://github.com/SublimeTextIssues/Core/issues/2924
        sublime.set_timeout( lambda: view.run_command( 'select_highlighted_previous_word_bug_fixer' ), 0 )


class SelectHighlightedPreviousWordBugFixerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()
        select_highlighted_previous_word_bug_fixer( view, selections )


def select_highlighted_previous_word_bug_fixer(view, selections):
    state = State( view )

    if not view.has_non_empty_selection_region():
        state.is_on_word_selection_mode = True

    # print( 'selections', [s for s in selections] )
    if selections:
        state.has_selected_new_word = False
        word_regions = view.get_regions( g_regionkey )

        if word_regions:
            settings = view.settings()
            copy_selected_text_into_find_panel = state.copy_selected_text_into_find_panel( settings )
            previous_word = run_previous_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

            if len( word_regions ) == len( selections ):
                sublime.status_message( "Selected all occurrences of the word '%s' on the file!" % view.substr( previous_word )[:100] )

            elif previous_word == word_regions[0]:
                    sublime.status_message( "Reached the first word '%s' on the file!" % view.substr( previous_word )[:100] )
                    state.select_previous_word_from_bottom = True

                    state.select_word_undo_stack.append( 'fake_previous' )
                    state.select_previous_word_skipped.append( word_regions[-1].end() )

                    if not state.has_selected_new_word:
                        run_previous_selection_search( view, word_regions, selections, copy_selected_text_into_find_panel )

            show_status_bar( view, selections, word_regions )


def run_previous_selection_search(view, word_regions, selections, copy_selected_text_into_find_panel):
    state = State( view )

    # print( 'select_previous_word_from_bottom', state.select_previous_word_from_bottom, state.select_previous_word_skipped )
    if state.select_previous_word_from_bottom:
        last_word = word_regions[-1]
        last_word_end = last_word.end() + 1

    else:
        last_word = state.selected_last_word[-1] if state.selected_last_word else selections[-1]
        last_word_end = last_word.begin() + 1

    # print( 'last_word_end', last_word_end, view.substr( last_word ), 'select_previous_word_skipped', state.select_previous_word_skipped, 'word_regions', word_regions )
    for previous_word in reversed( word_regions ):

        # print( 'previous_word_end', previous_word.end(), 'last_word_end', last_word_end, view.substr(previous_word) )
        if previous_word.begin() < last_word_end and previous_word.begin() < state.select_previous_word_skipped[-1]:

            if state.selected_first_word is None:
                state.selected_first_word = previous_word

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

            state.select_word_redo_stack.clear()
            state.select_word_undo_stack.append( 'previous' )
            state.select_previous_word_skipped.append( previous_word.begin() )

            state.has_selected_new_word = True
            state.selected_last_word.append( previous_word )
            break;

    debug_stack( timestamp, 'previous_word', get_selections_stack )
    return previous_word


class SelectHighlightedSkipPreviousWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view

        # https://github.com/SublimeTextIssues/Core/issues/2924
        sublime.set_timeout( lambda: view.run_command( 'select_highlighted_skip_previous_word_bug_fixer' ), 0 )


class SelectHighlightedSkipPreviousWordBugFixerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        selections = view.sel()
        word_regions = view.get_regions( g_regionkey )
        state = State( view )

        if selections and ( len( selections ) != len( word_regions ) or state.is_file_limit_reached ):

            if len( state.select_previous_word_skipped ) > 1 and len( selections ) > 1:
                unselect = state.selected_last_word.pop() if state.selected_last_word else selections[0]

                selections.subtract( unselect )
                select_highlighted_previous_word_bug_fixer( view, selections )

            else:
                select_highlighted_previous_word_bug_fixer( view, selections )
                select_highlighted_skip_previous_word_helper( view, selections, 1 )

        else:
            debug_stack( timestamp, 'skip_previous', get_selections_stack )


def select_highlighted_skip_previous_word_helper(view, selections, counter):
    counter -= 1

    if len( selections ) < 2:
        if counter < 0: return

        select_highlighted_previous_word_bug_fixer( view, selections )
        select_highlighted_skip_previous_word_helper( view, selections, counter )

    else:
        debug_stack( timestamp, 'skip_previous', get_selections_stack )
        state = State( view )

        unselect = state.selected_last_word.pop() if state.selected_last_word else selections[-1]
        selections.subtract( unselect )


class WordHighlightListener(sublime_plugin.EventListener):

    def on_text_command(self, view, command_name, args):
        # print('command_name', command_name, args)

        if command_name == 'soft_undo':
            state = State( view )

            if state.select_word_undo_stack:
                stack_type = state.select_word_undo_stack.pop()
                selected_last_word = state.selected_last_word.pop() if state.selected_last_word else None

                if state.selected_last_word:
                    view.show( state.selected_last_word[-1] )

                if stack_type == 'fake_next':
                    if state.select_word_undo_stack:
                        stack_type = state.select_word_undo_stack.pop()
                        state.select_next_word_skipped.pop()
                    else:
                        warning( "HighlightWordsOnSelection Error: 'soft_undo' empty stack", stack_type, get_selections_stack )

                elif stack_type == 'fake_previous':
                    if state.select_word_undo_stack:
                        stack_type = state.select_word_undo_stack.pop()
                        state.select_previous_word_skipped.pop()
                    else:
                        warning( "HighlightWordsOnSelection Error: 'soft_undo' empty stack", stack_type, get_selections_stack )

                if stack_type == 'next':
                    state.select_word_redo_stack.append( (state.select_next_word_skipped.pop(), 'next', selected_last_word) )

                elif stack_type == 'previous':
                    state.select_word_redo_stack.append( (state.select_previous_word_skipped.pop(), 'previous', selected_last_word) )

                else:
                    warning( "HighlightWordsOnSelection Error: 'soft_undo' got an invalid stack type", stack_type, get_selections_stack )

            debug_stack( timestamp, 'soft_undo', get_selections_stack )

        elif command_name == 'soft_redo':
            state = State( view )

            if state.select_word_redo_stack:
                elements = state.select_word_redo_stack.pop()
                skipped_word = elements[0]
                stack_type = elements[1]

                selected_last_word = elements[2]
                state.select_word_undo_stack.append( stack_type )

                if selected_last_word:
                    state.selected_last_word.append( selected_last_word )
                    view.show( selected_last_word )

                if stack_type == 'next':
                    state.select_next_word_skipped.append( skipped_word )

                elif stack_type == 'previous':
                    state.select_previous_word_skipped.append( skipped_word )

                else:
                    warning( "HighlightWordsOnSelection Error: 'soft_redo' got an invalid stack type", stack_type, get_selections_stack )

            debug_stack( timestamp, 'soft_redo', get_selections_stack )

        elif command_name == 'single_selection':
            clear_line_skipping( view, keep_whole_word_state=True )

        elif command_name == 'single_selection_first':
            state = State( view )

            if state.enable_find_under_expand_bug_fixes( view.settings() ) and state.selected_first_word is not None:
                state.blink_region = state.selected_first_word
                clear_line_skipping( view, keep_whole_word_state=True )

                def reset(): state.blink_region = None
                sublime.set_timeout( reset, CLEAR_CURSORS_CARETS_BLINKING )

                return ('clear_cursors_carets_single_selection_blinker', {
                        "message": "FIRST",
                        "region_start": state.blink_region.begin(),
                        "region_end": state.blink_region.end(),
                    })

            clear_line_skipping( view, keep_whole_word_state=True )

        elif command_name == 'single_selection_last':
            state = State( view )

            if state.enable_find_under_expand_bug_fixes( view.settings() ) and state.selected_last_word:
                state.blink_region = state.selected_last_word[-1]
                clear_line_skipping( view, keep_whole_word_state=True )

                def reset(): state.blink_region = None
                sublime.set_timeout( reset, CLEAR_CURSORS_CARETS_BLINKING )

                return ('clear_cursors_carets_single_selection_blinker', {
                        "message": "LAST",
                        "region_start": state.blink_region.begin(),
                        "region_end": state.blink_region.end(),
                    })

            clear_line_skipping( view, keep_whole_word_state=True )

        elif command_name == 'drag_select':

            if not ( 'additive' in args or 'subtractive' in args ):
                clear_line_skipping( view )

        elif command_name == 'move':
            clear_line_skipping( view )

    def on_query_context(self, view, key, operator, operand, match_all):

        if key == 'is_highlight_words_on_selection_working':
            state = State( view )
            return not state.is_file_limit_reached and view.get_regions( g_regionkey )

    def on_activated(self, view):

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
    state = State( view )

    # print('Reseting... keep_whole_word_state', keep_whole_word_state, state.blink_region)
    if ( not keep_whole_word_state or not view.has_non_empty_selection_region() ) and not state.blink_region:
        state.is_on_word_selection_mode = False

    # to to to too
    state.select_word_undo_stack.clear()
    state.select_word_redo_stack.clear()

    state.selected_first_word = None
    state.selected_last_word.clear()

    state.select_next_word_skipped = [ 0 ]
    state.select_previous_word_skipped = [ sys.maxsize ]

    state.select_next_word_from_beginning = False
    state.select_previous_word_from_bottom = False


def highlight_occurences(view):
    settings = view.settings()
    state = State( view )

    when_selection_is_empty = Pref.when_selection_is_empty( settings )
    are_all_selections_empty = not view.has_non_empty_selection_region()
    always_enable_selection_regions = Pref.always_enable_selection_regions( settings )

    # print( "has_non_empty_selection_region:", has_non_empty_selection_region )
    if are_all_selections_empty:
        clear_line_skipping( view )

        if not when_selection_is_empty and not always_enable_selection_regions:
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

    if view.size() <= Pref.file_size_limit( settings ):
        state.is_file_limit_reached = False

    else:
        state.is_file_limit_reached = True

    # print( 'running', str(time.time()) )
    word_regions = []
    processedWords = []
    occurrencesMessage = []
    occurrencesCount = 0
    word_separators = settings.get( 'word_separators' )

    for sel in selections:

        if sel.empty():

            if when_selection_is_empty or always_enable_selection_regions:
                string = view.substr(view.word(sel)).strip()

                if string not in processedWords:
                    processedWords.append(string)
                    is_word = all([not c in word_separators for c in string])

                    if string and is_word:
                        word_regions = find_regions(view, word_regions, string, True)

                    if not Pref.word_under_cursor_when_selection_is_empty( settings ):

                        for s in selections:
                            word_regions = [r for r in word_regions if not r.contains(s)]

        elif Pref.non_word_characters( settings ):
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

            if always_enable_selection_regions and not when_selection_is_empty and are_all_selections_empty:
                draw_outlined = sublime.HIDDEN

            else:
                draw_outlined = sublime.DRAW_NO_FILL if Pref.draw_outlined( settings ) else 0

            gutter = Pref.icon_type_on_gutter( settings ) if Pref.mark_occurrences_on_gutter( settings ) else ""

            view.add_regions( 'HighlightWordsOnSelection', word_regions, Pref.color_scope_name( settings ), gutter, draw_outlined )
            show_status_bar( view, selections, word_regions )

        else:
            view.erase_status( g_statusbarkey )

    elif not word_regions:
        view.erase_status( g_statusbarkey )
        view.erase_regions( g_regionkey )


def find_regions(view, word_regions, string, is_selection_empty):
    settings = view.settings()
    state = State( view )

    # to to to too
    if Pref.non_word_characters( settings ):
        if state.is_on_word_selection_mode or \
                Pref.only_whole_word_when_selection_is_empty( settings ) and is_selection_empty:
            search = r'\b' + escape_regex(string) + r'\b'

        else:
            search = escape_regex(string)

    else:
        # It seems as if \b doesn't pay attention to word_separators, but
        # \w does. Hence we use lookaround assertions instead of \b.
        if state.is_on_word_selection_mode or \
                Pref.only_whole_word_when_selection_is_empty( settings ) and is_selection_empty:
            search = r'\b(?<!\w)' + escape_regex(string) + r'(?!\w)\b'

        else:
            search = r'(?<!\w)' + escape_regex(string) + r'(?!\w)'

    if not state.is_file_limit_reached:
        word_regions += view.find_all( search, Pref.case_sensitive( settings ) )

    else:
        chars = Pref.when_file_size_limit_search_this_num_of_characters( settings )
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

