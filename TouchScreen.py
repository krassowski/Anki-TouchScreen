# -*- coding: utf-8 -*-
# Copyright: Michal Krassowski <krassowski.michal@gmail.com>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
"""
This plugin adds the function of touchscreen, similar that one implemented in AnkiDroid.

It adds a "view" menu entity (if it doesn't exist) with options like:

    switching touchscreen
    modifying some of the colors


If you want to contribute visit GitHub page: https://github.com/krassowski/Anki-TouchScreen
Also, feel free to send me bug reports or feature requests.

Copyright: Michal Krassowski <krassowski.michal@gmail.com>
License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html,
Important parts of Javascript code inspired by http://creativejs.com/tutorials/painting-with-pixels/index.html
"""

__addon_name__ = "TouchScreen"
__version__ = "0.1"

from aqt import mw, dialogs
from aqt.utils import showWarning


from anki.lang import _
from anki.hooks import addHook
from anki.hooks import wrap

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QAction, QKeySequence, QMenu, \
                        QColorDialog, QMessageBox, QColor, QInputDialog
from PyQt4 import QtCore
from os.path import isfile

try:
    nm_from_utf8 = QtCore.QString.fromUtf8
except AttributeError:
    nm_from_utf8 = lambda s: s

# This declarations are there only to be sure that in case of troubles
# with "profileLoaded" hook everything will work.

ts_state_on = False
ts_profile_loaded = False

ts_color = "#272828"
ts_line_width = 4
ts_default_review_html = mw.reviewer._revHtml

def ts_change_color():
    """
    Open color picker and set chosen color to text (in content)
    """
    global ts_color
    qcolor_old = QColor(ts_color)
    qcolor = QColorDialog.getColor(qcolor_old)
    if qcolor.isValid():
        ts_color = qcolor.name()
        execute_js("color = '" + ts_color + "'")
        ts_refresh()

def ts_change_width():
    global ts_line_width
    value, accepted = QInputDialog.getDouble(mw, "Touch Screen", "Enter the width:", ts_line_width)
    if accepted:
        ts_line_width = value
        execute_js("line_width = '" + str(ts_line_width) + "'")
        ts_refresh()
    
def ts_about():
    """
    Show "about" window.
    """
    ts_about_box = QMessageBox()
    ts_about_box.setText(__addon_name__ + " " + __version__ + __doc__)
    ts_about_box.setGeometry(300, 300, 250, 150)
    ts_about_box.setWindowTitle("About " + __addon_name__ + " " + __version__)

    ts_about_box.exec_()


def ts_save():
    """
    Saves configurable variables into profile, so they can
    be used to restore previous state after Anki restart.
    """
    mw.pm.profile['ts_state_on'] = ts_state_on
    mw.pm.profile['ts_color'] = ts_color
    mw.pm.profile['ts_line_width'] = ts_line_width



def ts_load():
    """
    Load configuration from profile, set states of checkable menu objects
    and turn on night mode if it were enabled on previous session.
    """
    global ts_state_on, ts_color, ts_profile_loaded

    try:
        ts_state_on = mw.pm.profile['ts_state_on']
        ts_color = mw.pm.profile['ts_color']
        ts_line_width = mw.pm.profile['ts_line_width']
    except KeyError:
        ts_state_on = False
        ts_color = "#f0f"
        ts_line_width = 4
    ts_profile_loaded = True

    if ts_state_on:
        ts_on()

def execute_js(code):
    web_object = mw.reviewer.web
    web_object.eval(code)


def clear_blackboard(web_object=None):

    if not web_object: 
        web_object = mw.reviewer.web

    if ts_state_on:
        javascript = """
        clear_canvas();
        """
        web_object.eval(javascript)



def ts_onload():
    """
    Add hooks and initialize menu.
    Call to this function is placed on the end of this file.
    """

    addHook("unloadProfile", ts_save)
    addHook("profileLoaded", ts_load)
    addHook("showQuestion", clear_blackboard)
    #ddHook("showAnswer", reshow_blackboard)

    ts_setup_menu()

ts_blackboard = u"""
<div id="canvas_wrapper">
    <canvas id="main_canvas" width="100" height="100"></canvas>
    <div id="pencil_button_bar">
        <input type="button" class="active" onclick="active=!active;switch_visibility();switch_class(this, 'active');" value="\u270D">
        <input type="button" class="active" onclick="clear_canvas();" value="\u2715"></div>
    </div>
</div>
<style>
#canvas_wrapper, #main_canvas
{
    position:absolute;
    top: 0px;
    left: 0px;
    z-index: 999;
}
#pencil_button_bar input[type=button].active
{
    color: #fff!important;
}
#pencil_button_bar
{
    position:absolute;
    top: 0px;
    right: 0px;    
}
#pencil_button_bar input[type=button]
{
    color:#444!important;
    background-color:rgba(10,10,10,0.5)!important;
    border: 1px solid black;
    margin:0px;
    display: inline-block;
    float:left;
    width:60px!important;
}
</style>

<script>

var visible = true;
var canvas = document.getElementById('main_canvas');
var ctx = canvas.getContext('2d');
var arrays_of_points = [ ];
var color = '#fff';
var line_width = 4;

function switch_visibility()
{
	if (visible)
	{
		canvas.style.display='none';
	}
	else
	{
		canvas.style.display='block';
	}
	visible = !visible;
}


function midPointBtw(p1, p2) {
  return {
    x: p1.x + (p2.x - p1.x) / 2,
    y: p1.y + (p2.y - p1.y) / 2
  };
}

function clear_canvas()
{
	ctx.clearRect(0, 0, canvas.width, canvas.height);
   	arrays_of_points=[];
}

function switch_class(e,c)
{
    var reg = new RegExp('(\\\s|^)' + c + '(\\s|$)');
	if (e.className.match(new RegExp('(\\s|^)' + c + '(\\s|$)')))
	{
		e.className = e.className.replace(reg, '');
	}
	else
	{
		e.className += c;
	}
}

function resize() {
	ctx.canvas.width = window.innerWidth;
	ctx.canvas.height = window.innerHeight;
	document.getElementById('canvas_wrapper').style.width = ctx.canvas.width + 'px';
}

resize();

window.addEventListener('resize', resize);

var isMouseDown = false;
var mouseX = 0;
var mouseY = 0;
var active = true;


canvas.addEventListener("mousedown",function (e) {
	isMouseDown = true;
	event.preventDefault();
	arrays_of_points.push(new Array());
	arrays_of_points[arrays_of_points.length-1].push({ x: e.offsetX, y: e.offsetY });
	ctx.lineJoin = ctx.lineCap = 'round';
	ctx.lineWidth = line_width;
	ctx.strokeStyle = color;
});
 
window.addEventListener("mouseup",function (e) {
    isMouseDown = false;
	//points.length = 0;
});
 
canvas.addEventListener("mousemove",function (e) {
    if (isMouseDown && active) {
        arrays_of_points[arrays_of_points.length-1].push({ x: e.offsetX, y: e.offsetY });
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        for (var path = 0; path < arrays_of_points.length; path++) {
            var p1 = arrays_of_points[path][0];
            var p2 = arrays_of_points[path][1];
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            for (var i = 1, len = arrays_of_points[path].length; i < len; i++) {
                var midPoint = midPointBtw(p1, p2);
                ctx.quadraticCurveTo(p1.x, p1.y, midPoint.x, midPoint.y);
                p1 = arrays_of_points[path][i];
                p2 = arrays_of_points[path][i+1];
            }
            ctx.lineTo(p1.x, p1.y);
            ctx.stroke();
        }
	}
});

</script>
"""

def ts_on():
    """
    Turn on
    """
    if not ts_profile_loaded:
        showWarning(NM_ERROR_NO_PROFILE)
        return False

    global ts_state_on

    try:
        ts_state_on = True
        
        mw.reviewer._revHtml = ts_default_review_html + ts_blackboard + \
        "<script>color = '" + ts_color + "'</script>" + "<script>line_width = '" + str(ts_line_width) + "'</script>"
        
        ts_menu_switch.setChecked(True)
        return True
    except:
        showWarning(NM_ERROR_SWITCH)
        return False


def ts_off():
    """
    Turn off
    """
    if not ts_profile_loaded:
        showWarning(NM_ERROR_NO_PROFILE)
        return False

    try:
        global ts_state_on
        ts_state_on = False

        mw.reviewer._revHtml = ts_default_review_html

        ts_menu_switch.setChecked(False)
        return True
    except:
        showWarning(NM_ERROR_SWITCH)
        return False


def ts_switch():
    """
    Switch TouchScreen.
    """

    if ts_state_on:
        ts_off()
    else:
        ts_on()

    # Reload current screen.
    if mw.state == "review":
        mw.reviewer._initWeb()
    if mw.state == "deckBrowser":
        mw.deckBrowser.refresh()
    if mw.state == "overview":
        mw.overview.refresh()


def ts_refresh():
    """
    Refresh display by reenabling night or normal mode.
    """
    if ts_state_on:
        ts_on()
    else:
        ts_off()


def ts_setup_menu():
    """
    Initialize menu. If there is an entity "View" in top level menu
    (shared with other plugins, like "Zoom" of R. Sieker) options of
    Night Mode will be putted there. In other case it creates that menu.
    """
    global ts_menu_switch

    try:
        mw.addon_view_menu
    except AttributeError:
        mw.addon_view_menu = QMenu(_(u"&View"), mw)
        mw.form.menubar.insertMenu(mw.form.menuTools.menuAction(),
                                    mw.addon_view_menu)

    mw.ts_menu = QMenu(_('&Touchscreen'), mw)

    mw.addon_view_menu.addMenu(mw.ts_menu)

    ts_menu_switch = QAction(_('&Enable touchscreen mode'), mw, checkable=True)
    ts_menu_color = QAction(_('Set &pen color'), mw)
    ts_menu_width = QAction(_('Set &pen width'), mw)
    ts_menu_about = QAction(_('&About...'), mw)

    ts_toggle_seq = QKeySequence("Ctrl+r")
    ts_menu_switch.setShortcut(ts_toggle_seq)

    mw.ts_menu.addAction(ts_menu_switch)
    mw.ts_menu.addAction(ts_menu_color)
    mw.ts_menu.addAction(ts_menu_width)
    mw.ts_menu.addSeparator()
    mw.ts_menu.addAction(ts_menu_about)

    s = SIGNAL("triggered()")
    mw.connect(ts_menu_switch, s, ts_switch)
    mw.connect(ts_menu_color, s, ts_change_color)
    mw.connect(ts_menu_width, s, ts_change_width)
    mw.connect(ts_menu_about, s, ts_about)

NM_ERROR_NO_PROFILE = "No profile loaded"

#
# ONLOAD SECTION
#

ts_onload()
