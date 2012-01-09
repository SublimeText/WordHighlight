What it does
------------

This plugin highlights all copies of a word that's currently selected, or,
optionally, highlights all copies of a word which currently has the insertion cursor upon it.

Install
-------

Go to your Packages subdirectory under ST2's data directory:

* Windows: %APPDATA%\Sublime Text 2
* OS X: ~/Library/Application Support/Sublime Text 2
* Linux: ~/.config/sublime-text-2
* Portable Installation: Sublime Text 2/Data

Then clone this repository:

    git clone git://github.com/SublimeText/WordHighlight.git
    
That's it!

Options
-------

Under the Packages/WordHighlight sub-directory, edit the `Word Highlight.sublime-settings` file:

*	`"draw_outlined" : true`
	
	This makes the highlights be drawn as outlines instead of as filled
	highlights.

*	`"highlight_when_selection_is_empty" : true`
	
	This makes words highlight when the insertion point is inside of them but when
	they're not actually selected.

*	`"highlight_word_under_cursor_when_selection_is_empty" : true`
	
	When the previous option is enabled, this makes the word under the cursor to gain highlighting

*	`"selection_delay" : 0`
	
	This delays highlighting all occurrences using given time (in miliseconds) to let users move cursor 
	around without being distracted with immediate highlights. Default value 0 means almost no delay.

*	`"color_scope_name" : "wordhighlight"`
	
	Normally the color of the highlights is the same as the color of comments in
	your code. If you'd like to customize the color, add the below to your color
	scheme file and change EDF2E9 to whatever color you want, then change
	color_scope_name to the scope name in the block you added.
	
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

* `"file_size_limit" : 4194304`
	
	Files bigger than this number will put WordHighlight on mode "highlight around view port" (a portion of the document)

* `"when_file_size_limit_search_this_num_of_characters" : 20000`
	
	When a file is bigger than the previous setting. This controls how many characters below and above the  view port you want to search for words to highlight

