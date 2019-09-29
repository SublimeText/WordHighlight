What it does
------------

This plugin highlights all copies of a word that's currently selected, or,
optionally, highlights all copies of a word which currently has the insertion cursor upon it.

Additionally you may select all these words highlighted with <kbd>ALT</kbd>+<kbd>ENTER</kbd>, or also may append to the selection these words one by one similar to <kbd>CTRL</kbd>+<kbd>D</kbd>.

If you would like to use the settings:
```js
    "highlight_words_on_selection.copy_selected_text_into_find_panel": true,
    "highlight_words_on_selection.blink_selection_on_single_selection": true,
```

You also need to install these packages:
1. https://github.com/evandrocoan/FixedToggleFindPanel
1. https://github.com/evandrocoan/ClearCursorsCarets


## Installation

### By Package Control

1. Download & Install `Sublime Text 3` (https://www.sublimetext.com/3)
1. Go to the menu `Tools -> Install Package Control`, then,
   wait few seconds until the `Package Control` installation finishes
1. Go to the menu `Preferences -> Package Control`
1. Type `Package Control Add Channel` on the opened quick panel and press <kbd>Enter</kbd>
1. Then, input the following address and press <kbd>Enter</kbd>
   ```
   https://raw.githubusercontent.com/evandrocoan/StudioChannel/master/channel.json
   ```
1. Now, go again to the menu `Preferences -> Package Control`
1. This time type `Package Control Install Package` on the opened quick panel and press <kbd>Enter</kbd>
1. Then, search for `HighlightWordsOnSelection` and press <kbd>Enter</kbd>

See also:
1. [ITE - Integrated Toolset Environment](https://github.com/evandrocoan/ITE)
1. [Package control docs](https://packagecontrol.io/docs/usage) for details.


Options
-------

Under the Packages/HighlightWordsOnSelection sub-directory, edit the `HighlightWordsOnSelection.sublime-settings` file:

*   `"draw_outlined" : true`

    This makes the highlights be drawn as outlines instead of as filled
    highlights.
*   `"mark_occurrences_on_gutter" : true`

    If this comes true, icons will be used to mark all occurrences of selected words on the gutter bar.
    To customize the icons, the property "icon_type_on_gutter" is helpful.

*   `"icon_type_on_gutter" : dot`

    Normally, there are 4 valid types: dot, circle, bookmark and cross. If you want more, please
    have a look at folder "Theme - Default" under the "Packages" of Sublime Text (this can be done
    via menu "Preferences > Browse Packages").

*   `"highlight_when_selection_is_empty" : true`

    This makes words highlight when the insertion point is inside of them but when
    they're not actually selected.

*   `"highlight_word_under_cursor_when_selection_is_empty" : true`

    When the previous option is enabled, this makes the word under the cursor to gain highlighting

*   `"highlight_delay" : 0`

    This delays highlighting all occurrences using given time (in milliseconds) to let users move cursor
    around without being distracted with immediate highlights. Default value 0 means almost no delay.

*   `"show_word_highlight_status_bar_message" : true`

    This lets you toggle if you want a status bar message to show how many occurrences of the highlighted word there are.
    If you mix this with `"highlight_word_under_cursor_when_selection_is_empty": false` the occurrence number will not count word your cursor is on.

*   `"color_scope_name" : "wordhighlight"`

    Normally the color of the highlights is the same as the color of comments in
    your code. If you'd like to customize the color, add the below to your color
    scheme `.tmTheme` file and change EDF2E9 to whatever color you want, then change
    color_scope_name to the scope name in the block you added. If you'd like to
    specify a background color, uncomment the background part in the example below
    and set "draw_outlined" to "false").
    ```xml
    <dict>
        <key>name</key>
        <string>WordHighlight</string>
        <key>scope</key>
        <string>wordhighlight</string>
        <key>settings</key>
        <dict>
            <key>foreground</key>
            <string>#EDF2E9</string>

            <!--
            <key>background</key>
            <string>#16DD00</string>
            -->
        </dict>
    </dict>
    ```
    Note that some other plugins such as Color Hightlighter and SublimeLinter make copies
    of your tmTheme and add their own modifications, and if you are using a plugin that
    does this, your change to the `.tmTheme` file may not be reflected in the UI immediately.

* `"file_size_limit" : 4194304`

    Files bigger than this number will put HighlightWordsOnSelection on mode "highlight around view port" (a portion of the document)

* `"when_file_size_limit_search_this_num_of_characters" : 20000`

    When a file is bigger than the previous setting. This controls how many characters below and above the  view port you want to search for words to highlight

Selections
-------

By default it provides the key <kbd>ALT</kbd>+<kbd>ENTER</kbd> to select all the words highlighted by this package (you may highlight multiple words and then select all the instances)

It also has two functions with no keymap defined, to mimic <kbd>CTRL</kbd>+<kbd>D</kbd> and <kbd>CTRL</kbd>+<kbd>K</kbd>, <kbd>CTRL</kbd>+<kbd>D</kbd>. You may decided to use the alternatives by adding (upon customization) the following to the keymap file (`Packages/User/Default (Windows).sublime-keymap`):

```json
{ "keys": ["ctrl+enter"], "command": "select_highlighted_next_word", "context":
    [   { "key": "selection_empty", "operator": "equal", "operand": false },
        { "key": "setting.is_widget", "operator": "equal", "operand": false }
    ]
},
{ "keys": ["ctrl+backspace"], "command": "select_highlighted_skip_last_word", "context":
    [   { "key": "selection_empty", "operator": "equal", "operand": false },
        { "key": "setting.is_widget", "operator": "equal", "operand": false }
    ]
},
```


License
--------

See the file [LICENSE](LICENSE)

