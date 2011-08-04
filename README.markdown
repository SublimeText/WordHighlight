What it does
------------

This plugin highlights all copies of a word that's currently selected, or,
optionally, selects all copies of a word that contains an insertion point.


Options
-------

*	`"draw_outlined" : true`
	
	This makes the highlights be drawn as outlines instead of as filled
	highlights.

*	`"highlight_when_selection_is_empty" : true`
	
	This makes words highlight when the insertion point is inside of them but when
	they're not actually selected.

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
