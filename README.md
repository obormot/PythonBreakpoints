Sublime Text Python Breakpoints
===============================

This is a [Sublime Text](http://www.sublimetext.com) plugin allowing to quickly set Python breakpoints by injecting set_trace() call of pdb or other debugger of your choice.

## Features

* breakpoint color highlighting, gutter icons
* auto indentation, auto save on toggle (off by default, configurable)
* your source file stores all breakpoints; plugin detects and recreates them on next load
* support for user comments to help navigate among many breakpoints

## Screenshot

<img src=https://raw.githubusercontent.com/obormot/PythonBreakpoints/master/screenshot.png>

## Install

Through [Package Control](https://sublime.wbond.net/packages/Package%20Control) (recommended):

`Command Palette` > `Package Control: Install Package` > `Python Breakpoints`

From GitHub: Clone this repository into your version/platform specific Packages directory. Example for Mac and ST2 (note the space in the target directory name):

    cd ~/Library/Application Support/Sublime Text 2/Packages
    git clone https://github.com/obormot/PythonBreakpoints 'Python Breakpoints'

## Usage

`Command Palette` > `Python Breakpoints: ...`

* `Toggle` a breakpoint at current line (or `ctrl+shift+b`)
* `Goto` a selected breakpoint (or `ctrl+shift+g`, or `Menu` > `Goto` > `Goto Python Breakpoint...`)
* `Clear All` breakpoints in current file (or `Menu` > `Tools` > `Breakpoints` > `Clear All Python Breakpoints`)

## Settings

`Preferences` > `Package Settings` > `Python Breakpoints`

## Caveats

* only space indentation is supported
* in some code fragments the plugin may incorrectly indent the breakpoint; in such cases just use Indent/Unindent keyboard shortcuts to move it into desired position
