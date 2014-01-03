# -*- coding: utf-8 -*-
"""
Python Breakpoints plugin for Sublime Text editor

Author: Oscar Ibatullin (github.com/obormot)
"""

from __future__ import print_function
import ast
import re
import uuid

import sublime
import sublime_plugin


############
# Settings #
############

settings = sublime.load_settings("PythonBreakpoints.sublime-settings")

tab_size = settings.get('tab_size')
if tab_size == 'auto' or tab_size == None:
    g_settings = sublime.load_settings('Preferences.sublime-settings')
    tab_size = g_settings.get('tab_size', 4)

debug = lambda *a: None  # replace with debug = print if needed


#############
# Constants #
#############

pdb_block = """\
try:  # do not edit! added by PythonBreakpoints
    from ipdb import set_trace as _breakpoint
except ImportError:
    from pdb import set_trace as _breakpoint


"""

bp_regex = r"^[\t ]*_breakpoint\(\)  # ([a-f0-9]{8})"
bp_re = re.compile(bp_regex, re.DOTALL)

EXPR_PRE = ['class', 'def', 'if', 'for', 'try', 'while', 'with']
EXPR_PST = ['elif', 'else', 'except', 'finally']

expr_re0 = re.compile(r"^[\t ]*(%s)[: ]" % '|'.join(EXPR_PRE))
expr_re1 = re.compile(r"^[\t ]*(%s)[: ]" % '|'.join(EXPR_PRE + EXPR_PST))
expr_re2 = re.compile(r"^[\t ]*(%s)[: ]" % '|'.join(EXPR_PST))


class Breakpoint(object):
    """
    Breakpoint object with its UID
    """
    def __init__(self, from_text=None):
        self.uid = None
        if from_text is not None:
            m = bp_re.match(from_text)
            if m:
                self.uid = m.groups()[0]
        else:
            self.uid = str(uuid.uuid4())[-8:]

    @property
    def rg_key(self):
        """breakpoint's region ID"""
        return 'bp-%s' % self.uid

    def format(self, indent):
        """format breakpoint string"""
        return "%s_breakpoint()  # %s\n" % (' ' * indent, self.uid)

    def highlight(self, view, rg):
        """colorize the breakpoint's region"""
        scope = settings.get('highlight', 'invalid')
        view.add_regions(self.rg_key, [rg], scope)


###################
# Helper routines #
###################

def is_python(view):
    return view.match_selector(0, 'source.python')


def save_file(view):
    save_on_toggle = settings.get('save_on_toggle', True)
    if save_on_toggle and view.is_dirty() and view.file_name():
        view.run_command('save')


def ln_from_region(view, rg):  # line number from region
    return view.rowcol(rg.end())[0]


def goto_position(view, pos):  # move cursor to position
    view.sel().clear()
    view.sel().add(pos)


def calc_pdb_position(view):
    """
    find and return injection spot for the pdb_block; None on failure
    """
    size = view.size()
    text = view.substr(sublime.Region(0, size))

    # make a few tries to compile the AST
    # if code contains errors strip at line before the error and retry
    for i in range(5):
        try:
            # parse through import statements to find a sweet spot for the
            # pdb_block injection, outside of any complex/multiline import
            # constructs, preferrably after the last import statement
            fst = imp = nxt = None
            for node in ast.iter_child_nodes(ast.parse(text)):
                if type(node) in (ast.Import, ast.ImportFrom):
                    if not fst:
                        fst = node.lineno
                    imp = node.lineno
                elif not fst:
                    fst = node.lineno
                elif imp:
                    nxt = node.lineno
                    break
            ln = nxt if nxt else imp if imp else fst
            return view.text_point(ln - 1 if ln > 1 else ln, 0)
        except (IndentationError, SyntaxError) as e:
            lines = view.lines(sublime.Region(0, size))
            debug('err in line %d %r' % (
                  e.lineno, view.substr(lines[e.lineno - 1])))
            size = lines[e.lineno - 2].begin()
            text = view.substr(sublime.Region(0, size))


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
    _indent = lambda x: len(x) - len(x.lstrip())
    curr_indent = _indent(curr_line)
    prev_indent = _indent(prev_line)
    next_indent = _indent(next_line)
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


def find_pdb_block(view):
    """return position of the pdb_block, or None"""
    rg = view.find(pdb_block.strip(), 0, sublime.LITERAL)
    if rg:
        return rg.begin()


def find_breakpoint(view):
    """return position of the 1st breakpoint, or None"""
    rg = view.find(bp_regex, 0)
    if rg:
        return rg.end()


def remove_pdb_block(edit, view):
    pos = find_pdb_block(view)
    rg = sublime.Region(pos, pos + len(pdb_block))
    assert pdb_block in view.substr(rg), rg
    view.erase(edit, rg)


def remove_breakpoint(edit, view, rg):
    """
    find and remove the breakpoint, return True on success
    """
    rg = view.full_line(rg)
    lines = view.lines(sublime.Region(0, rg.end()))
    ln = min(ln_from_region(view, rg), len(lines) - 1)

    for line in (lines[ln], lines[ln - 1]):  # search current and prev lines
        bp = Breakpoint(view.substr(line))
        if bp.uid:
            view.erase(edit, view.full_line(line))
            view.erase_regions(bp.rg_key)
            return True
    return False


def insert_pdb_block(edit, view):
    """
    inject the pdb_block construct, return its position
    """
    pos = calc_pdb_position(view)
    if pos is not None:
        view.insert(edit, pos, pdb_block)
        return pos


def insert_breakpoint(edit, view, rg):
    bp = Breakpoint()
    rg_a = rg.begin()
    indent = calc_indent(view, rg)
    if indent is not None:
        bp_rg_sz = view.insert(edit, rg_a, bp.format(indent))
        color_rg = sublime.Region(rg_a, rg_a + bp_rg_sz)
        bp.highlight(view, color_rg)
        goto_position(view, rg_a + indent)


###############
# ST commands #
###############

class ToggleBreakpointCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view

        # don't handle non-Python and selected text
        if not (is_python(view) and view.sel()[0].empty()):
            return

        # check/insert the pdb_block
        pdb_pos = find_pdb_block(view)
        if pdb_pos is None:
            pdb_pos = insert_pdb_block(edit, view)

        # remove/insert the breakpoint
        rg = view.line(view.sel()[0])
        if remove_breakpoint(edit, view, rg):
            # if no more breakpoints remove pdb_block
            if not find_breakpoint(view):
                remove_pdb_block(edit, view)
        else:
            # inserting a new breakpoint below pdb_block
            if pdb_pos and rg.begin() >= pdb_pos + len(pdb_block):
                insert_breakpoint(edit, view, rg)
            # if insertion didn't happen undo the pdb_block
            elif not find_breakpoint(view) and find_pdb_block(view):
                remove_pdb_block(edit, view)
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
            ln = ln_from_region(view, rg)

            # grab 2 next non-empty code lines
            for j, l in enumerate(lines[ln - 1:]):
                s = view.substr(l)
                if not s.strip():   # skip empty lines
                    continue
                if not j:           # strip the 1st line
                    s = s.strip()
                lnn = ln_from_region(view, l) + 1

                items[i].append('%d: %s' % (lnn, s))
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

            if find_pdb_block(view):
                remove_pdb_block(edit, view)

            save_file(view)


##################
# Event listener #
##################

class PythonBreakpointEventListener(sublime_plugin.EventListener):

    def on_load(self, view):
        """
        on file load, scan it for breakpoints and highlight them
        """
        if is_python(view) and find_pdb_block(view):
            for rg in view.find_all(bp_regex, 0):
                bp = Breakpoint(view.substr(rg))
                bp.highlight(view, rg)
