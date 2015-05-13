# -*- coding: utf-8 -*-
"""
Python Breakpoints plugin for Sublime Text 2/3

Author: Oscar Ibatullin (github.com/obormot)

"""
from __future__ import print_function
import re
import sys
import uuid

import sublime
import sublime_plugin


############
# Settings #
############

# replace with "debug = print" to print debug messages to the ST console
debug = lambda *a: None

# defaults
settings = None
tab_size = 4


def plugin_loaded():
    global settings
    settings = sublime.load_settings('PythonBreakpoints.sublime-settings')

    global tab_size
    tab_size = settings.get('tab_size')
    if tab_size == 'auto' or tab_size is None:
        g_settings = sublime.load_settings('Preferences.sublime-settings')
        tab_size = g_settings.get('tab_size', 4)


# for ST2
if sys.version_info < (3,):
    plugin_loaded()


#############
# Constants #
#############

bp_regex = r"^[\t ]*import [\w.; ]+set_trace\(\)  # breakpoint ([a-f0-9]{8})([a-z]?) //"
bp_re = re.compile(bp_regex, re.DOTALL)

EXPR_PRE = ['class', 'def', 'if', 'for', 'try', 'while', 'with']
EXPR_PST = ['elif', 'else', 'except', 'finally']

expr_re0 = re.compile(r"^[\t ]*({tokens})[: ]".format(tokens='|'.join(EXPR_PRE)))
expr_re1 = re.compile(r"^[\t ]*({tokens})[: ]".format(tokens='|'.join(EXPR_PRE + EXPR_PST)))
expr_re2 = re.compile(r"^[\t ]*({tokens})[: ]".format(tokens='|'.join(EXPR_PST)))

TRY_STR = 'try:'
EXCEPT_STR = 'except Exception as exc:'


class Breakpoint(object):
    """
    Breakpoint object with its UID
    """
    def __init__(self, from_text=None, in_block=False):
        self.uid = None
        self.in_block = in_block
        if from_text is not None:
            m = bp_re.match(from_text)
            if m:
                self.uid = m.groups()[0]
                self.in_block = m.groups()[1] == 'x'
        else:
            self.uid = str(uuid.uuid4())[-8:]

    @property
    def region_id(self):
        """
        breakpoint's region ID
        """
        return "bp-{uid}".format(uid=self.uid)

    def as_string(self, indent):
        """
        format breakpoint string
        """
        debugger = settings.get('debugger', 'pdb')
        return "{indent}import {dbg}; {dbg}.set_trace()  # breakpoint {uid}{mark} //\n".format(
            indent=' ' * indent, dbg=debugger, uid=self.uid, mark='x' if self.in_block else '')

    def highlight(self, view, rg):
        """
        colorize the breakpoint's region
        """
        scope = settings.get('highlight', 'invalid')
        gutter_icon = settings.get('gutter_icon', 'circle')
        view.add_regions(self.region_id, [rg], scope, gutter_icon, sublime.PERSISTENT)


###################
# Helper routines #
###################

def is_python(view):
    return view.match_selector(0, 'source.python')


def save_file(view):
    save_on_toggle = settings.get('save_on_toggle', False)
    if save_on_toggle and view.is_dirty() and view.file_name():
        view.run_command('save')


def get_indent(s):
    """
    return number of spaces left of the first non-whitespace character in s
    """
    return len(s) - len(s.lstrip())


def get_line_number(view, rg):
    """
    line number from region
    """
    return view.rowcol(rg.end())[0]


def goto_position(view, pos):
    """
    move cursor to position
    """
    view.sel().clear()
    view.sel().add(pos)


def calc_indent(view, rg):
    """
    calculate indentation for the inserted breakpoint statement
    """
    ln = None

    # clean up regions that are empty or comment lines
    lines = view.lines(sublime.Region(0, view.size()))
    for l in list(lines):
        if l == rg:  # don't remove the current line
            ln = lines.index(l)
        else:
            line = view.substr(l).strip()
            if not line or line.startswith('#'):
                lines.remove(l)
            elif ln is not None:
                break  # reached current and next line

    # a couple of hacks to handle corner cases
    if not ln:
        ln = -1

    if ln + 1 >= len(lines):
        lines.append(lines[-1])

    # calculate vertical distance to previous and next lines
    prev_dist = lines[ln].begin() - lines[ln - 1].end()
    next_dist = lines[ln + 1].begin() - lines[ln].end()
    debug('distance p', prev_dist, 'n', next_dist)

    if next_dist < 0:
        next_dist = 0xff

    curr_line = view.substr(lines[ln])
    prev_line = view.substr(lines[ln - 1])
    next_line = view.substr(lines[ln + 1])

    # calculate indent of current, previous and next lines
    curr_indent = get_indent(curr_line)
    prev_indent = get_indent(prev_line)
    next_indent = get_indent(next_line)
    debug('indent p', prev_indent, 'c', curr_indent, 'n', next_indent)

    def _result(msg, indent):
        debug(msg)
        # check if previous or next line already contains a breakpoint
        # at the same indent level
        c1 = indent == prev_indent and bp_re.match(prev_line)
        c2 = indent == next_indent and bp_re.match(next_line) and not curr_line
        if not (c1 or c2):
            return indent

    # order of checks is critical!
    if expr_re1.match(prev_line):
        if prev_dist < next_dist:
            return _result('re1-1', prev_indent + tab_size)
        else:
            return _result('re1-2', curr_indent)

    if expr_re0.match(curr_line):
        if prev_dist < next_dist:
            return _result('re0-1', prev_indent)
        else:
            return _result('re0-2', curr_indent)

    if expr_re2.match(next_line):
        if prev_dist <= next_dist:
            return _result('re2-1', curr_indent)
        else:
            return _result('re2-3', next_indent)

    if expr_re1.match(curr_line):
        return _result('re1-3', curr_indent + tab_size)

    # go heuristic - choose the closest indent
    if curr_line:
        return _result('he0', curr_indent)
    elif prev_dist <= next_dist:
        return _result('he1-1', prev_indent)
    else:
        return _result('he1-2', next_indent)


def find_breakpoint(view):
    """
    return position of the 1st breakpoint, or None
    """
    rg = view.find(bp_regex, 0)
    return rg.end() if rg else None


def remove_breakpoint(edit, view, rg):
    """
    find and remove the breakpoint, return True on success
    """
    rg = view.full_line(rg)
    lines = view.lines(sublime.Region(0, rg.end()))
    ln = min(get_line_number(view, rg), len(lines) - 1)

    for line in (lines[ln], lines[ln - 1]):  # search current and prev lines
        bp = Breakpoint(view.substr(line))
        if bp.uid:
            view.erase(edit, view.full_line(line))
            view.erase_regions(bp.region_id)
            if bp.in_block:
                # remove the try-except block
                indent = None
                for pline in reversed(lines[:ln]):
                    if pline == line:
                        continue

                    s = view.substr(pline)

                    # first, find the "except:" block
                    if indent is None:
                        if s.strip().startswith(EXCEPT_STR):
                            indent = get_indent(s)
                            view.erase(edit, view.full_line(pline))
                        continue

                    # it's a "try:" at the same indent level, finish
                    if s.startswith(' ' * indent + TRY_STR):
                        view.erase(edit, view.full_line(pline))
                        break

                    # else outdent each line within the try-except block
                    indent_rg = sublime.Region(pline.begin(), pline.begin() + tab_size)
                    view.erase(edit, indent_rg)
            return True
    return False


def insert_breakpoint(edit, view, rg):
    indent = calc_indent(view, rg)
    if indent is None:
        return

    bp = Breakpoint()
    rg_a = rg.begin()
    bp_rg_sz = view.insert(edit, rg_a, bp.as_string(indent))
    color_rg = sublime.Region(rg_a, rg_a + bp_rg_sz)
    bp.highlight(view, color_rg)
    goto_position(view, rg_a + indent)


def insert_try_except_breakpoint(edit, view, rgs):
    # find first non-empty non-comment line in the selection and get its indent
    indent = None
    for rg in rgs:
        line = view.substr(rg).strip()
        if line and not line.startswith('#'):
            indent = get_indent(view.substr(rg))
            break

    if indent is None:  # nothing worthwhile in the selection
        return

    rg_a = rgs[0].begin()
    rg_b = view.full_line(rgs[-1]).end()
    indent_str = ' ' * indent

    # insert "try:" at the same indent level
    offset = view.insert(edit, rg_a, "{}{}\n".format(indent_str, TRY_STR))

    # add one level of indentation to every line in the block
    for rg in rgs:
        offset += view.insert(edit, rg.begin() + offset, ' ' * tab_size)

    offset += view.insert(edit, rg_b + offset, "{}{}\n".format(indent_str, EXCEPT_STR))

    # insert the breakpoint
    bp = Breakpoint(in_block=True)
    rg_a = rg_b + offset
    bp_rg_sz = view.insert(edit, rg_a, bp.as_string(indent + tab_size))
    color_rg = sublime.Region(rg_a, rg_a + bp_rg_sz)
    bp.highlight(view, color_rg)
    goto_position(view, rg_a + indent + tab_size)


###############
# ST commands #
###############

class ToggleBreakpointCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view

        # don't handle non-Python
        if not is_python(view):
            return

        # is there a selected text?
        if view.sel()[0].empty():
            # remove/insert a one-line breakpoint
            rg = view.line(view.sel()[0])
            if not remove_breakpoint(edit, view, rg):
                insert_breakpoint(edit, view, rg)
            save_file(view)
        else:
            # wrap the selected text in try-except
            rgs = view.lines(view.sel()[0])
            insert_try_except_breakpoint(edit, view, rgs)
            save_file(view)


class GotoBreakpointCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        if not is_python(view):
            return

        bp_regions = view.find_all(bp_regex, 0)
        items = [[] for __ in bp_regions]
        lines = view.lines(sublime.Region(0, view.size()))

        for i, rg in enumerate(bp_regions):
            rg = view.full_line(rg)
            ln = get_line_number(view, rg)

            # grab 2 next non-empty code lines
            for j, l in enumerate(lines[ln - 1:]):
                s = view.substr(l)
                if not s.strip():   # skip empty lines
                    continue
                if not j:           # strip the 1st line
                    s = s.strip()
                lnn = get_line_number(view, l) + 1

                if bp_re.match(s):
                    s = s[s.find('# breakpoint') + 2:]

                items[i].append('{}: {}'.format(lnn, s))
                if len(items[i]) > 2:
                    break

        def on_done(idx):
            if idx > -1:
                goto_position(view, bp_regions[idx].end())
                view.show_at_center(bp_regions[idx])

        if items:
            view.window().show_quick_panel(items, on_done)


class ClearAllBreakpointsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        if is_python(view):
            for i in range(999):  # put a hard limit, just in case
                rg = find_breakpoint(view)
                if not (rg and remove_breakpoint(edit, view, rg)):
                    break
            save_file(view)


##################
# Event listener #
##################

class PythonBreakpointEventListener(sublime_plugin.EventListener):

    def on_load(self, view):
        """
        on file load, scan it for breakpoints and highlight them
        """
        if is_python(view):
            for rg in view.find_all(bp_regex, 0):
                bp = Breakpoint(view.substr(rg))
                bp.highlight(view, rg)
