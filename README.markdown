What it does
------------

This plugin highlights all copies of a word that's currently selected, or,
optionally, highlights all copies of a word which currently has the insertion cursor upon it.

Additionally you may select all these words highlighted with `ALT+ENTER`, or also may append to the selection these words one by one similar to CTRL+D.

Install
-------

The easiest method to install would be using [Package Control](https://sublime.wbond.net/installation).
Ensure you have the latest by visiting that link, then open the command palette, type in
"Install Package", and search for "WordHighLight".

Alternatively, to manually install go to your Packages subdirectory under ST's data directory, where `X` is the ST version:

* Windows: %APPDATA%\Sublime Text X
* OS X: ~/Library/Application Support/Sublime Text X
* Linux: ~/.config/sublime-text-X
* Portable Installation: Sublime Text X/Data

Then clone this repository:

    git clone git://github.com/SublimeText/WordHighlight.git

That's it!

Options
-------

Under the Packages/WordHighlight sub-directory, edit the `Word Highlight.sublime-settings` file:

*	`"draw_outlined" : true`

	This makes the highlights be drawn as outlines instead of as filled
	highlights.
*	`"mark_occurrences_on_gutter" : true`

	If this comes true, icons will be used to mark all occurrences of selected words on the gutter bar.
	To customize the icons, the property "icon_type_on_gutter" is helpful.

*	`"icon_type_on_gutter" : dot`

	Normally, there are 4 valid types: dot, circle, bookmark and cross. If you want more, please
	have a look at folder "Theme - Default" under the "Packages" of Sublime Text (this can be done
    via menu "Preferences > Browse Packages").

*	`"highlight_when_selection_is_empty" : true`

	This makes words highlight when the insertion point is inside of them but when
	they're not actually selected.

*	`"highlight_word_under_cursor_when_selection_is_empty" : true`

	When the previous option is enabled, this makes the word under the cursor to gain highlighting

*	`"highlight_delay" : 0`

	This delays highlighting all occurrences using given time (in milliseconds) to let users move cursor
	around without being distracted with immediate highlights. Default value 0 means almost no delay.

*	`"show_word_highlight_status_bar_message" : true`

	This lets you toggle if you want a status bar message to show how many occurrences of the highlighted word there are.
	If you mix this with `"highlight_word_under_cursor_when_selection_is_empty": false` the occurrence number will not count word your cursor is on.

*	`"color_scope_name" : "wordhighlight"`

	Normally the color of the highlights is the same as the color of comments in
	your code. If you'd like to customize the color, add the below to your color
	scheme file and change EDF2E9 to whatever color you want, then change
	color_scope_name to the scope name in the block you added. If you'd like to
	specify a background color, uncomment the background part in the example below
	and set "draw_outlined" to "false").

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

* `"file_size_limit" : 4194304`

	Files bigger than this number will put WordHighlight on mode "highlight around view port" (a portion of the document)

* `"when_file_size_limit_search_this_num_of_characters" : 20000`

	When a file is bigger than the previous setting. This controls how many characters below and above the  view port you want to search for words to highlight

Selections
-------

By default it provides the key `ALT+ENTER` to select all the words highlighted by this package (you may highlight multiple words and then select all the instances)

It also has two functions with no keymap defined, to mimic `CTRL+D` and `CTRL+K, CTRL+D`. You may decided to use the alternatives by adding (upon customization) the following to the keymap file (`Packages/User/Default (Windows).sublime-keymap`):

```
	{ "keys": ["ctrl+enter"], "command": "select_highlighted_next_word", "context":
		[	{ "key": "selection_empty", "operator": "equal", "operand": false },
			{ "key": "setting.is_widget", "operator": "equal", "operand": false }
		]
	},
	{ "keys": ["ctrl+backspace"], "command": "select_highlighted_skip_last_word", "context":
		[	{ "key": "selection_empty", "operator": "equal", "operand": false },
			{ "key": "setting.is_widget", "operator": "equal", "operand": false }
		]
	},
```