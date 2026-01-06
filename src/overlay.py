import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo


class SelectionManager:
    """Manages region selection using a transparent fullscreen overlay."""

    def __init__(self):
        # Selection state
        self.start_x = self.start_y = 0
        self.end_x = self.end_y = 0
        self.is_dragging = False
        self.selection = None  # (x, y, w, h) when complete

        # Border window for visual feedback
        self.border_window = BorderWindow()

        # Toolbar for start/abort buttons
        self.toolbar = ToolbarWindow()

        # Callbacks
        self.on_selection_complete = None
        self.on_cancel = None
        self.on_start_recording = None
        self.on_stop_recording = None

        # Fullscreen transparent overlay for capturing mouse events
        self._overlay = Gtk.Window(type=Gtk.WindowType.POPUP)
        self._overlay.set_decorated(False)
        self._overlay.set_app_paintable(True)
        self._overlay.set_keep_above(True)

        # Enable RGBA for true transparency
        screen = self._overlay.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self._overlay.set_visual(visual)

        # Set up events
        self._overlay.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.KEY_PRESS_MASK
        )
        self._overlay.connect('draw', self._on_draw)
        self._overlay.connect('button-press-event', self.on_button_press)
        self._overlay.connect('button-release-event', self.on_button_release)
        self._overlay.connect('motion-notify-event', self.on_motion)
        self._overlay.connect('key-press-event', self.on_key_press)
        self._overlay.set_can_focus(True)

        # Wire up toolbar callbacks
        self.toolbar.on_start = self._toolbar_start
        self.toolbar.on_stop = self._toolbar_stop
        self.toolbar.on_abort = self._toolbar_abort
        self.toolbar.on_drag = self._on_drag
        self.border_window.on_drag = self._on_drag

    def _toolbar_start(self):
        if self.on_start_recording:
            self.on_start_recording()

    def _toolbar_stop(self):
        if self.on_stop_recording:
            self.on_stop_recording()

    def _toolbar_abort(self):
        self.cancel()

    def _on_drag(self, dx, dy):
        """Handle drag to reposition selection."""
        if self.selection:
            x, y, w, h = self.selection
            x += int(dx)
            y += int(dy)
            self.selection = (x, y, w, h)
            self.border_window.set_position(x, y)
            self.toolbar.position_below(self.selection)

    def _on_draw(self, widget, cr):
        # Paint completely transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

    def show_for_selection(self):
        self.selection = None
        self.border_window.rect = None
        self.border_window.hide()
        self.toolbar.hide()
        self.is_dragging = False

        # Cover the entire screen
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geometry = monitor.get_geometry()

        # For multi-monitor, get full screen bounds
        n_monitors = display.get_n_monitors()
        min_x = min_y = 0
        max_x = max_y = 0
        for i in range(n_monitors):
            mon = display.get_monitor(i)
            geom = mon.get_geometry()
            min_x = min(min_x, geom.x)
            min_y = min(min_y, geom.y)
            max_x = max(max_x, geom.x + geom.width)
            max_y = max(max_y, geom.y + geom.height)

        self._overlay.move(min_x, min_y)
        self._overlay.resize(max_x - min_x, max_y - min_y)
        self._overlay.show_all()
        self._overlay.present()

        # Set crosshair cursor
        cursor = Gdk.Cursor.new_from_name(display, 'crosshair')
        self._overlay.get_window().set_cursor(cursor)

        # Grab keyboard focus for Escape key
        self._overlay.grab_focus()

    def on_button_press(self, widget, event):
        if event.button == 1:  # Left click
            self.start_x = int(event.x_root)
            self.start_y = int(event.y_root)
            self.is_dragging = True
        elif event.button == 3:  # Right click to cancel
            self.cancel()

    def on_motion(self, widget, event):
        if self.is_dragging:
            self.end_x = int(event.x_root)
            self.end_y = int(event.y_root)
            self.border_window.update_rect(
                self.start_x, self.start_y,
                self.end_x, self.end_y
            )

    def on_button_release(self, widget, event):
        if self.is_dragging and event.button == 1:
            self.is_dragging = False
            self.end_x = int(event.x_root)
            self.end_y = int(event.y_root)

            self._overlay.hide()

            # Calculate normalized rectangle
            x = min(self.start_x, self.end_x)
            y = min(self.start_y, self.end_y)
            w = abs(self.end_x - self.start_x)
            h = abs(self.end_y - self.start_y)

            if w > 10 and h > 10:  # Minimum size
                # Snap to even dimensions for H.264 compatibility
                # Round down to avoid extending into the border
                w = w - (w % 2)
                h = h - (h % 2)

                self.selection = (x, y, w, h)
                # Update border to match snapped dimensions
                self.border_window.update_from_selection(x, y, w, h)

                # Show toolbar below selection
                self.toolbar.position_below(self.selection)
                if self.on_selection_complete:
                    self.on_selection_complete(self.selection)
            else:
                # Selection too small, cancel
                self.border_window.hide()
                if self.on_cancel:
                    self.on_cancel()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.cancel()

    def cancel(self):
        self.is_dragging = False
        self._overlay.hide()
        self.border_window.hide()
        self.toolbar.hide()
        if self.on_cancel:
            self.on_cancel()

    def set_recording(self, recording):
        self.border_window.set_recording(recording)
        self.toolbar.set_recording(recording)


class ToolbarWindow(Gtk.Window):
    """Floating toolbar with Start/Abort buttons - draggable to reposition selection."""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_keep_above(True)

        # Callbacks
        self.on_start = None
        self.on_stop = None
        self.on_abort = None
        self.on_drag = None  # Called with (dx, dy) delta

        self._recording = False

        # Drag state
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Event box for drag handling on the toolbar background
        self.event_box = Gtk.EventBox()
        self.event_box.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.event_box.connect('button-press-event', self._on_drag_start)
        self.event_box.connect('button-release-event', self._on_drag_end)
        self.event_box.connect('motion-notify-event', self._on_drag_motion)

        # Create buttons
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        self.start_btn = Gtk.Button(label="Start Recording")
        self.start_btn.connect('clicked', self._on_start_clicked)
        self.start_btn.get_style_context().add_class('suggested-action')

        self.abort_btn = Gtk.Button(label="Cancel")
        self.abort_btn.connect('clicked', self._on_abort_clicked)

        box.pack_start(self.start_btn, True, True, 0)
        box.pack_start(self.abort_btn, True, True, 0)
        self.event_box.add(box)
        self.add(self.event_box)

    def set_recording(self, recording):
        """Update button state for recording mode."""
        self._recording = recording
        if recording:
            self.start_btn.set_label("Finish and Save")
            self.abort_btn.set_sensitive(False)
        else:
            self.start_btn.set_label("Start Recording")
            self.abort_btn.set_sensitive(True)

    def _on_start_clicked(self, button):
        if self._recording:
            if self.on_stop:
                self.on_stop()
        else:
            if self.on_start:
                self.on_start()

    def _on_abort_clicked(self, button):
        if self.on_abort:
            self.on_abort()

    def _on_drag_start(self, widget, event):
        if event.button == 1:
            self._dragging = True
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root

    def _on_drag_end(self, widget, event):
        self._dragging = False

    def _on_drag_motion(self, widget, event):
        if self._dragging and self.on_drag:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self.on_drag(dx, dy)

    def position_below(self, rect):
        """Position toolbar centered below the selection rectangle."""
        x, y, w, h = rect
        self.show_all()

        # Get toolbar size after showing
        self.queue_resize()
        while Gtk.events_pending():
            Gtk.main_iteration()

        toolbar_w = self.get_allocation().width
        if toolbar_w < 10:
            toolbar_w = 200  # Fallback

        # Center below selection
        pos_x = x + (w - toolbar_w) // 2
        pos_y = y + h + 8  # 8px gap below selection

        self.move(pos_x, pos_y)


class BorderWindow(Gtk.Window):
    """Border rectangle - draggable on border, click-through in center."""

    BORDER_WIDTH = 6  # Width of draggable border area

    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_app_paintable(True)

        # Enable RGBA for transparent background
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.rect = None
        self.recording = False
        self.on_drag = None  # Callback for drag (dx, dy)

        # Drag state
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Events
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.connect('draw', self.on_draw)
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self.connect('motion-notify-event', self._on_motion)
        self.connect('realize', self._on_realize)

    def _on_realize(self, widget):
        """Set input shape to only receive events on the border, not center."""
        self._update_input_shape()

    def _update_input_shape(self):
        """Make center click-through, only border receives input."""
        if not self.get_realized() or not self.rect:
            return

        window = self.get_window()
        if not window:
            return

        alloc = self.get_allocation()
        w, h = alloc.width, alloc.height
        border = self.BORDER_WIDTH

        # Create region covering the whole window
        region = cairo.Region(cairo.RectangleInt(0, 0, w, h))

        # Subtract the center (make it click-through)
        if w > border * 2 and h > border * 2:
            center = cairo.RectangleInt(border, border, w - border * 2, h - border * 2)
            region.subtract(cairo.Region(center))

        window.input_shape_combine_region(region, 0, 0)

    def _on_button_press(self, widget, event):
        if event.button == 1 and not self.recording:
            self._dragging = True
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root

    def _on_button_release(self, widget, event):
        self._dragging = False

    def _on_motion(self, widget, event):
        if self._dragging and self.on_drag:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self.on_drag(dx, dy)

    def update_rect(self, x1, y1, x2, y2):
        """Update border during drag - shows live preview."""
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        if w > 0 and h > 0:
            self.rect = (x, y, w, h)
            border = self.BORDER_WIDTH
            window_x = x - border
            window_y = y - border
            window_w = w + border * 2
            window_h = h + border * 2
            self.move(window_x, window_y)
            self.resize(window_w, window_h)
            self.show_all()
            self.queue_draw()
            self._update_input_shape()

    def update_from_selection(self, x, y, w, h):
        """Update border to match final snapped selection."""
        self.rect = (x, y, w, h)
        border = self.BORDER_WIDTH
        self.move(x - border, y - border)
        self.resize(w + border * 2, h + border * 2)
        self.queue_draw()
        self._update_input_shape()

    def set_position(self, x, y):
        """Move the border to a new position."""
        if self.rect:
            _, _, w, h = self.rect
            self.rect = (x, y, w, h)
            border = self.BORDER_WIDTH
            self.move(x - border, y - border)
            self._update_input_shape()

    def set_recording(self, recording):
        self.recording = recording
        self.queue_draw()
        self._update_input_shape()  # Disable dragging during recording

    def on_draw(self, widget, cr):
        if not self.rect:
            return

        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        border = self.BORDER_WIDTH

        # Clear to transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Draw border
        if self.recording:
            cr.set_source_rgb(1, 0, 0)  # Red when recording
        else:
            cr.set_source_rgb(1, 1, 1)  # White when ready

        cr.set_line_width(border)
        cr.rectangle(border / 2, border / 2, w - border, h - border)
        cr.stroke()
