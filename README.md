Sublime Text Python Breakpoints
===============================

This is a [Sublime Text](http://www.sublimetext.com) plugin allowing to quickly set Python breakpoints by injecting [i]pdb.set_trace().

## Features

* breakpoint color highlighting
* auto indentation, auto save on toggle (off by default, configurable)
* your source file stores all breakpoints; plugin detects and recreates them on next load

## Install

Through [Package Control](https://sublime.wbond.net/packages/Package%20Control)

`Command Palette` > `Package Control: Install Package` > `PythonBreakpoints`

or clone this repository into your version/platform specific Packages directory.

## Usage

`Command Palette` > `Breakpoints: ...`

* `Toggle` a breakpoint at current line (or `ctrl+shift+b`)
* `Goto` a selected breakpoint (or `alt+g` / `cmd+g`, or `Menu` > `Goto` > `Goto Breakpoint...`)
* `Clear All` breakpoints in current file (or `Menu` > `Tools` > `Breakpoints` > `Clear All`)

## Settings

`Preferences` > `Package Settings` > `PythonBreakpoints`

## Caveats

* minimally tested with ST3 and on Windows
* with non-PEP8 one-liners or files with no imports your mileage may vary
