Sublime Text Python Breakpoints
===============================

This is a [Sublime Text](http://www.sublimetext.com) plugin allowing to quickly set Python breakpoints by injecting set_trace() call of pdb or other debugger of your choice.

## Features

* breakpoint color highlighting
* auto indentation, auto save on toggle (off by default, configurable)
* your source file stores all breakpoints; plugin detects and recreates them on next load

## Install

Through [Package Control](https://sublime.wbond.net/packages/Package%20Control):

`Command Palette` > `Package Control: Install Package` > `Python Breakpoints`

From GitHub: Clone this repository into your version/platform specific Packages directory. Example for Mac and ST2 (note the space in the target directory name):

    cd ~/Library/Application Support/Sublime Text 2/Packages
    git clone https://github.com/obormot/PythonBreakpoints 'Python Breakpoints'

## Usage

`Command Palette` > `Python Breakpoints: ...`

* `Toggle` a breakpoint at current line (or `ctrl+shift+b`)
* `Goto` a selected breakpoint (or `alt+g` / `cmd+g`, or `Menu` > `Goto` > `Goto Python Breakpoint...`)
* `Clear All` breakpoints in current file (or `Menu` > `Tools` > `Breakpoints` > `Clear All Python Breakpoints`)

## Settings

`Preferences` > `Package Settings` > `Python Breakpoints`

## Caveats

* only space indentation is supported
* with non-PEP8 one-liners or files with no imports your mileage may vary

