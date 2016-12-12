# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib, Gdk, GObject, Pango

from gettext import gettext as _

from lollypop.define import Lp, ArtSize, Type, NextContext
from lollypop.define import WindowSize, Shuffle, Loading
from lollypop.widgets_track import TracksWidget, TrackRow
from lollypop.widgets_context import ContextWidget
from lollypop.objects import Track, Album
from lollypop.widgets_rating import RatingWidget
from lollypop.pop_menu import AlbumMenuPopover, AlbumMenu
from lollypop.pop_artwork import CoversPopover


class BaseWidget:
    """
        Base album widget
    """

    def __init__(self):
        """
            Init widget
        """
        self._selected = None
        self._loading = Loading.NONE
        self._cover = None
        self._widget = None
        self._play_all_button = None
        self._artwork_button = None
        self._action_button = None
        self._show_overlay = False
        self._lock_overlay = False
        self._timeout_id = None
        self.__parent_filter = False
        self._overlay_orientation = Gtk.Orientation.HORIZONTAL
        self._squared_class = "squared-icon"
        self._rounded_class = "rounded-icon"

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        pass

    def update_duration(self, track_id):
        """
            Update duration for current track
            @param track id as int
        """
        pass

    def stop(self):
        """
            Stop populating
        """
        self._loading = Loading.STOP

    def set_filtered(self, b):
        """
            Set widget filtered
        """
        self.__parent_filter = b

    @property
    def filter(self):
        return ""

    @property
    def filtered(self):
        """
            True if filtered by parent
        """
        return self.__parent_filter

    @property
    def is_overlay(self):
        """
            True if overlayed or going to be
        """
        return self._show_overlay or self._timeout_id is not None

    def lock_overlay(self, lock):
        """
            Lock overlay
            @param lock as bool
        """
        self._lock_overlay = lock

    def show_overlay(self, set):
        """
            Set overlay
            @param set as bool
        """
        # Remove enter notify timeout
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self._show_overlay_func(set)

#######################
# PROTECTED           #
#######################
    def _set_play_all_image(self):
        """
            Set play all image based on current shuffle status
        """
        if Lp().settings.get_enum('shuffle') == Shuffle.NONE:
            self._play_all_button.set_from_icon_name(
                                        'media-playlist-consecutive-symbolic',
                                        Gtk.IconSize.BUTTON)
        else:
            self._play_all_button.set_from_icon_name(
                                        'media-playlist-shuffle-symbolic',
                                        Gtk.IconSize.BUTTON)

    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set:
            return
        self._show_overlay = set
        self.emit('overlayed', set)
        if set:
            if Lp().player.locked:
                opacity = 0.2
            else:
                opacity = 1
            if self._play_button is not None:
                self._play_button.set_opacity(opacity)
                self._play_button.get_style_context().add_class(
                                                           self._rounded_class)
                self._play_button.show()
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(opacity)
                self._play_all_button.get_style_context().add_class(
                                                           self._squared_class)
                self._set_play_all_image()
                self._play_all_button.show()
            if self._artwork_button is not None:
                self._artwork_button.set_opacity(1)
                self._artwork_button.get_style_context().add_class(
                                                           self._squared_class)
                self._artwork_button.show()
            if self._action_button is not None:
                self._show_append(not Lp().player.has_album(self._album))
                self._action_button.set_opacity(opacity)
                self._action_button.get_style_context().add_class(
                                                       self._squared_class)
                self._action_button.show()
        else:
            if self._play_button is not None:
                self._play_button.set_opacity(0)
                self._play_button.hide()
                self._play_button.get_style_context().remove_class(
                                                           self._rounded_class)
            if self._play_all_button is not None:
                self._play_all_button.set_opacity(0)
                self._play_all_button.hide()
                self._play_all_button.get_style_context().remove_class(
                                                           self._squared_class)
            if self._artwork_button is not None:
                self._artwork_button.hide()
                self._artwork_button.set_opacity(0)
                self._artwork_button.get_style_context().remove_class(
                                                           self._squared_class)
            if self._action_button is not None:
                self._action_button.hide()
                self._action_button.set_opacity(0)
                self._action_button.get_style_context().remove_class(
                                                           self._squared_class)

    def _on_eventbox_realize(self, eventbox):
        """
            Change cursor over eventbox
            @param eventbox as Gdk.Eventbox
        """
        window = eventbox.get_window()
        if window is not None:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def _on_enter_notify(self, widget, event):
        """
            Show overlay buttons after a timeout
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        self._cover.set_opacity(0.9)
        if self._timeout_id is None:
            self._timeout_id = GLib.timeout_add(250,
                                                self.__on_enter_notify_timeout)

    def _on_leave_notify(self, widget, event):
        """
            Hide overlay buttons
            @param widget as Gtk.Widget
            @param event es Gdk.Event
        """
        allocation = widget.get_allocation()
        if event.x <= 0 or\
           event.x >= allocation.width or\
           event.y <= 0 or\
           event.y >= allocation.height:
            self._cover.set_opacity(1)
            # Remove enter notify timeout
            if self._timeout_id is not None:
                GLib.source_remove(self._timeout_id)
                self._timeout_id = None
            if self._show_overlay:
                self._show_overlay_func(False)

    def _on_play_press_event(self, widget, event):
        """
            Play album
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if Lp().player.locked:
            return True
        Lp().player.play_album(self._album)
        self._show_append(False)
        return True

    def _on_artwork_press_event(self, widget, event):
        """
            Popover with album art downloaded from the web (in fact google :-/)
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        popover = CoversPopover(self._album)
        popover.set_relative_to(widget)
        popover.connect('closed', self._on_pop_cover_closed)
        self._lock_overlay = True
        popover.show()
        return True

    def _on_action_press_event(self, widget, event):
        """
            Append album to current list if not present
            Remove it if present
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if Lp().player.locked:
            return True
        if Lp().player.has_album(self._album):
            if Lp().player.current_track.album.id == self._album.id:
                # If not last album, skip it
                if len(Lp().player.get_albums()) > 1:
                    Lp().player.skip_album()
                    Lp().player.remove_album(self._album)
                # remove it and stop playback by going to next track
                else:
                    Lp().player.remove_album(self._album)
                    Lp().player.set_next()
                    Lp().player.next()
            else:
                Lp().player.remove_album(self._album)
            self._show_append(True)
        else:
            if Lp().player.is_playing() and not Lp().player.get_albums():
                Lp().player.play_album(self._album)
            else:
                Lp().player.add_album(self._album)
            self._show_append(False)
        return True

    def _on_pop_cover_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self._lock_overlay = False
        GLib.idle_add(self.show_overlay, False)

    def _show_append(self, append):
        """
            Show append button if append, else remove button
        """
        if append:
            self._action_button.set_from_icon_name('list-add-symbolic',
                                                   Gtk.IconSize.BUTTON)
            self._action_event.set_tooltip_text(_("Append"))
        else:
            self._action_button.set_from_icon_name('list-remove-symbolic',
                                                   Gtk.IconSize.BUTTON)
            self._action_event.set_tooltip_text(_("Remove"))

#######################
# PRIVATE             #
#######################
    def __on_enter_notify_timeout(self):
        """
            Show overlay buttons
        """
        self._timeout_id = None
        if not self._show_overlay:
            self._show_overlay_func(True)


class AlbumWidget(BaseWidget):
    """
        Album widget
    """

    def __init__(self, album_id, genre_ids=[],
                 artist_ids=[], art_size=ArtSize.BIG):
        """
            Init Album widget
        """
        BaseWidget.__init__(self)
        self._album = Album(album_id, genre_ids)
        self._filter_ids = artist_ids
        self._art_size = art_size
        self.connect('destroy', self.__on_destroy)
        self._scan_signal = Lp().scanner.connect('album-updated',
                                                 self._on_album_updated)

    @property
    def album(self):
        """
            @return Album
        """
        return self._album

    @property
    def id(self):
        """
            Return widget id
        """
        return self._album.id

    @property
    def filter(self):
        """
            @return str
        """
        return " ".join([self._album.name]+self._album.artists)

    def get_cover(self):
        """
            Get album cover
            @return cover as Gtk.Image
        """
        return self._cover

    def set_cover(self):
        """
            Set cover for album if state changed
        """
        if self._cover is None:
            return
        surface = Lp().art.get_album_artwork(
                            self._album,
                            self._art_size,
                            self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        if surface.get_height() > surface.get_width():
            self._overlay_orientation = Gtk.Orientation.VERTICAL
        else:
            self._overlay_orientation = Gtk.Orientation.HORIZONTAL
        del surface

    def update_cover(self):
        """
            Update cover for album id id needed
        """
        if self._cover is None:
            return
        surface = Lp().art.get_album_artwork(
                            self._album,
                            self._art_size,
                            self._cover.get_scale_factor())
        self._cover.set_from_surface(surface)
        if surface.get_height() > surface.get_width():
            self._overlay_orientation = Gtk.Orientation.VERTICAL
        else:
            self._overlay_orientation = Gtk.Orientation.HORIZONTAL
        del surface

    def update_state(self):
        """
            Update widget state
        """
        if self._cover is None or self._art_size != ArtSize.BIG:
            return
        selected = self._album.id == Lp().player.current_track.album.id
        if selected != self._selected:
            if selected:
                self._cover.get_style_context().add_class(
                                                    'cover-frame-selected')
            else:
                self._cover.get_style_context().remove_class(
                                                    'cover-frame-selected')

#######################
# PROTECTED           #
#######################
    def _on_album_updated(self, scanner, album_id, destroy):
        pass

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, widget):
        """
            Disconnect signal
            @param widget as Gtk.Widget
        """
        if self._scan_signal is not None:
            Lp().scanner.disconnect(self._scan_signal)


class AlbumSimpleWidget(Gtk.FlowBoxChild, AlbumWidget):
    """
        Album widget showing cover, artist and title
    """
    __gsignals__ = {
        'overlayed': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album_id, genre_ids, artist_ids):
        """
            Init simple album widget
            @param album id as int
            @param genre ids as [int]
            @param artist_ids as [int]
        """
        # We do not use Gtk.Builder for speed reasons
        Gtk.FlowBoxChild.__init__(self)
        self.set_size_request(ArtSize.BIG, ArtSize.BIG)
        self.get_style_context().add_class('loading')
        AlbumWidget.__init__(self, album_id, genre_ids, artist_ids)

    def populate(self):
        """
            Populate widget content
        """
        self.get_style_context().remove_class('loading')
        self._rounded_class = "rounded-icon-small"
        self._widget = Gtk.EventBox()
        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self._cover = Gtk.Image()
        self._cover.set_property('halign', Gtk.Align.CENTER)
        self._cover.get_style_context().add_class('cover-frame')
        self.__title_label = Gtk.Label()
        self.__title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__title_label.set_property('halign', Gtk.Align.CENTER)
        self.__title_label.set_markup("<b>" +
                                      GLib.markup_escape_text(
                                                            self._album.name) +
                                      "</b>")
        self.__artist_label = Gtk.Label()
        self.__artist_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.__artist_label.set_property('halign', Gtk.Align.CENTER)
        self.__artist_label.set_text(", ".join(self._album.artists))
        self.__artist_label.get_style_context().add_class('dim-label')
        self._widget.set_property('has-tooltip', True)
        self._widget.connect('query-tooltip', self._on_query_tooltip)
        self._widget.add(grid)
        self.__overlay = Gtk.Overlay.new()
        self.__overlay.set_property('halign', Gtk.Align.CENTER)
        self.__overlay.set_property('valign', Gtk.Align.CENTER)
        self.__overlay_grid = Gtk.Grid()
        self.__overlay_grid.set_column_spacing(6)
        self.__overlay_grid.set_row_spacing(6)
        self.__overlay_grid.set_margin_top(6)
        self.__overlay_grid.set_margin_bottom(6)
        self.__overlay_grid.set_margin_start(6)
        self.__overlay_grid.set_margin_end(6)
        self.__overlay.add(self._cover)
        self.__overlay.add_overlay(self.__overlay_grid)
        color = Gtk.Grid()
        color.set_property('halign', Gtk.Align.CENTER)
        color.set_property('valign', Gtk.Align.CENTER)
        color.get_style_context().add_class('white')
        color.add(self.__overlay)
        grid.add(color)
        grid.add(self.__title_label)
        grid.add(self.__artist_label)
        self.add(self._widget)
        self.set_cover()
        self.update_state()
        self._widget.set_property('halign', Gtk.Align.CENTER)
        self._widget.set_property('valign', Gtk.Align.CENTER)
        self.show_all()
        self._widget.connect('enter-notify-event', self._on_enter_notify)
        self._widget.connect('leave-notify-event', self._on_leave_notify)
        if self._album.is_web:
            self._cover.get_style_context().add_class(
                                                'cover-frame-web')

    def do_get_preferred_width(self):
        """
            Return preferred width
            @return (int, int)
        """
        # Padding: 3px, border: 1px + spacing
        width = ArtSize.BIG + 12
        return (width, width)

#######################
# PROTECTED           #
#######################
    def _show_overlay_func(self, set):
        """
            Set overlay
            @param set as bool
        """
        if self._lock_overlay or\
           self._show_overlay == set:
            return
        if set:
            # Play button
            self._play_event = Gtk.EventBox()
            self._play_event.set_property('has-tooltip', True)
            self._play_event.set_tooltip_text(_("Play"))
            self._play_event.connect('realize', self._on_eventbox_realize)
            self._play_event.connect('button-press-event',
                                     self._on_play_press_event)
            self._play_button = Gtk.Image.new_from_icon_name(
                                               'media-playback-start-symbolic',
                                               Gtk.IconSize.BUTTON)
            self._play_button.set_opacity(0)
            # Play all button
            self._play_all_event = Gtk.EventBox()
            self._play_all_event.set_property('has-tooltip', True)
            self._play_all_event.set_tooltip_text(_("Play albums"))
            self._play_all_event.set_property('halign', Gtk.Align.END)
            self._play_all_event.connect('realize', self._on_eventbox_realize)
            self._play_all_event.connect('button-press-event',
                                         self.__on_play_all_press_event)
            self._play_all_button = Gtk.Image.new()
            self._play_all_button.set_opacity(0)
            # Artwork button
            self._artwork_event = Gtk.EventBox()
            self._artwork_event.set_property('has-tooltip', True)
            self._artwork_event.set_tooltip_text(_("Change artwork"))
            self._artwork_event.set_property('halign', Gtk.Align.END)
            self._artwork_event.connect('realize', self._on_eventbox_realize)
            self._artwork_event.connect('button-press-event',
                                        self._on_artwork_press_event)
            self._artwork_button = Gtk.Image.new_from_icon_name(
                                               'image-x-generic-symbolic',
                                               Gtk.IconSize.BUTTON)
            self._artwork_button.set_opacity(0)
            # Action button
            self._action_event = Gtk.EventBox()
            self._action_event.set_property('has-tooltip', True)
            self._action_event.set_property('halign', Gtk.Align.END)
            self._action_event.connect('realize', self._on_eventbox_realize)
            self._action_event.connect('button-press-event',
                                       self._on_action_press_event)
            self._action_button = Gtk.Image.new()
            self._action_button.set_opacity(0)
            self.__overlay_grid.set_orientation(self._overlay_orientation)
            if self._overlay_orientation == Gtk.Orientation.VERTICAL:
                self._play_event.set_hexpand(False)
                self._play_event.set_vexpand(True)
                self._play_event.set_property('halign', Gtk.Align.END)
                self._play_event.set_property('valign', Gtk.Align.START)
                self.__overlay_grid.set_property('valign', Gtk.Align.FILL)
                self.__overlay_grid.set_property('halign', Gtk.Align.END)
            else:
                self._play_event.set_hexpand(True)
                self._play_event.set_vexpand(False)
                self._play_event.set_property('halign', Gtk.Align.START)
                self._play_event.set_property('valign', Gtk.Align.END)
                self.__overlay_grid.set_property('halign', Gtk.Align.FILL)
                self.__overlay_grid.set_property('valign', Gtk.Align.END)
            self._play_event.add(self._play_button)
            self._play_all_event.add(self._play_all_button)
            self._artwork_event.add(self._artwork_button)
            self._action_event.add(self._action_button)
            self.__overlay_grid.add(self._play_event)
            self.__overlay_grid.add(self._play_all_event)
            self.__overlay_grid.add(self._action_event)
            self.__overlay_grid.add(self._artwork_event)
            self.__overlay_grid.show_all()
            AlbumWidget._show_overlay_func(self, True)
        else:
            AlbumWidget._show_overlay_func(self, False)
            self._play_event.destroy()
            self._play_event = None
            self._play_button.destroy()
            self._play_button = None
            self._play_all_event.destroy()
            self._play_all_event = None
            self._play_all_button.destroy()
            self._play_all_button = None
            self._action_event.destroy()
            self._action_event = None
            self._action_button.destroy()
            self._action_button = None
            self._artwork_event.destroy()
            self._artwork_event = None
            self._artwork_button.destroy()
            self._artwork_button = None

    def _on_album_updated(self, scanner, album_id, destroy):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param deleted as bool
            @param destroy as bool
        """
        if self._album.id == album_id and destroy:
            self.destroy()

#######################
# PRIVATE             #
#######################
    def __on_play_all_press_event(self, widget, event):
        """
            Play album with context
            @param: widget as Gtk.EventBox
            @param: event as Gdk.Event
        """
        if Lp().player.locked:
            return True
        self._show_append(False)
        if Lp().player.is_party:
            Lp().player.set_party(False)
        Lp().player.clear_albums()
        track = Track(self._album.track_ids[0])
        if Lp().window.view.filtered:
            # Here we need to get ids from parent as view may be filtered
            for child in self.get_parent().get_children():
                if not child.filtered:
                    Lp().player.add_album(child.album)
        else:
            Lp().player.set_albums(track.id, self._filter_ids,
                                   self._album.genre_ids)
        Lp().player.load(track)
        return True

    def _on_query_tooltip(self, eventbox, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param eventbox as Gtk.EventBox
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        eventbox.set_tooltip_text('')
        for widget in [self.__title_label, self.__artist_label]:
            layout = widget.get_layout()
            if layout.is_ellipsized():
                artist_text = self.__artist_label.get_text()
                if artist_text:
                    text = "<b>%s</b> - %s" % (
                        GLib.markup_escape_text(artist_text),
                        GLib.markup_escape_text(self.__title_label.get_text()))
                else:
                    text = GLib.markup_escape_text(
                                                 self.__title_label.get_text())
                eventbox.set_tooltip_markup(text)
                break


class AlbumDetailedWidget(Gtk.Bin, AlbumWidget):
    """
        Widget with cover and tracks
    """
    __gsignals__ = {
        'populated': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'overlayed': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, album_id, genre_ids, artist_ids, art_size):
        """
            Init detailed album widget
            @param album id as int
            @param genre ids as [int]
            @param artist ids as [int]
            @param lazy as LazyLoadingView
            @param art size as ArtSize
        """
        Gtk.Bin.__init__(self)
        AlbumWidget.__init__(self, album_id, genre_ids, artist_ids, art_size)
        self._album.set_artists(artist_ids)
        self.__width = None
        self.__context = None
        # Cover + rating + spacing
        self.__height = ArtSize.BIG + 26
        self.__orientation = None
        self.__child_height = TrackRow.get_best_height(self)
        # Header + separator + spacing + margin
        self.__requested_height = self.__child_height + 6
        # Discs to load, will be emptied
        self.__discs = self._album.discs
        self.__locked_widget_right = True
        self.set_property('height-request', self.__height)
        self.connect('size-allocate', self.__on_size_allocate)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/AlbumDetailedWidget.ui')
        builder.connect_signals(self)
        self._widget = builder.get_object('widget')
        album_info = builder.get_object('albuminfo')
        title_label = builder.get_object('title')
        year_label = builder.get_object('year')
        self.__header = builder.get_object('header')
        self.__overlay = builder.get_object('overlay')
        self.__duration_label = builder.get_object('duration')
        self._play_button = builder.get_object('play-button')
        self._artwork_button = builder.get_object('artwork-button')
        self._action_button = builder.get_object('action-button')
        self._action_event = builder.get_object('action-event')
        self.__context_button = builder.get_object('context')

        artist_label = builder.get_object('artist')
        if art_size == ArtSize.NONE:
            self._cover = None
            self.__rating = RatingWidget(self._album)
            self.__rating.set_hexpand(True)
            self.__rating.set_property('halign', Gtk.Align.END)
            self.__rating.set_property('valign', Gtk.Align.CENTER)
            self.__header.attach(self.__rating, 4, 0, 1, 1)
            self.__rating.show()
            artist_label.set_text(", ".join(self._album.artists))
            artist_label.show()
            if self._album.year:
                year_label.set_label(self._album.year)
                year_label.show()
        else:
            self.__duration_label.set_hexpand(True)
            if art_size == ArtSize.BIG:
                if self._album.year:
                    year_label.set_label(self._album.year)
                    year_label.show()
                builder = Gtk.Builder()
                builder.add_from_resource('/org/gnome/Lollypop/CoverBox.ui')
                self._cover = builder.get_object('cover')
                self._cover.get_style_context().add_class('cover-frame')
                self.__coverbox = builder.get_object('coverbox')
                # 6 for 2*3px (application.css)
                self.__coverbox.set_property('width-request', art_size + 6)
                self.__rating = RatingWidget(self._album)
                self.__coverbox.add(self.__rating)
                self.__rating.show()
                self._widget.attach(self.__coverbox, 0, 0, 1, 1)
                if Lp().window.get_view_width() < WindowSize.MEDIUM:
                    self.__coverbox.hide()
                if len(artist_ids) > 1:
                    artist_label.set_text(", ".join(self._album.artists))
                    artist_label.show()
            elif art_size == ArtSize.HEADER:
                self._cover = Gtk.Image()
                self._cover.set_halign(Gtk.Align.CENTER)
                self._cover.set_margin_bottom(5)
                self._cover.get_style_context().add_class('small-cover-frame')
                self._cover.show()
                builder.get_object('albuminfo').attach(self._cover,
                                                       0, 0, 1, 1)
                artist_label.set_text(", ".join(self._album.artists))
                artist_label.show()

        self.__set_duration()

        self.__box = Gtk.Grid()
        self.__box.set_column_homogeneous(True)
        self.__box.set_property('valign', Gtk.Align.START)
        self.__box.show()
        album_info.add(self.__box)

        self._tracks_left = {}
        self._tracks_right = {}

        self.set_cover()
        self.update_state()

        title_label.set_label(self._album.name)

        for disc in self.__discs:
            self.__add_disc_container(disc.number)
            self.__set_disc_height(disc)

        self.add(self._widget)
        # We start transparent, we switch opaque at size allocation
        # This prevent artifacts
        self.set_opacity(0)

        if self._album.is_web and self._cover is not None:
            self._cover.get_style_context().add_class(
                                                'cover-frame-web')

    def update_playing_indicator(self):
        """
            Update playing indicator
        """
        for disc in self._album.discs:
            self._tracks_left[disc.number].update_playing(
                Lp().player.current_track.id)
            self._tracks_right[disc.number].update_playing(
                Lp().player.current_track.id)

    def update_duration(self, track_id):
        """
            Update duration for current track
            @param track id as int
        """
        for disc in self._album.discs:
            self._tracks_left[disc.number].update_duration(track_id)
            self._tracks_right[disc.number].update_duration(track_id)

    def populate(self):
        """
            Populate tracks
            @thread safe
        """
        if self.__discs:
            disc = self.__discs.pop(0)
            mid_tracks = int(0.5 + len(disc.tracks) / 2)
            self.populate_list_left(disc.tracks[:mid_tracks],
                                    disc,
                                    1)
            self.populate_list_right(disc.tracks[mid_tracks:],
                                     disc,
                                     mid_tracks + 1)

    def is_populated(self):
        """
            Return True if populated
            @return bool
        """
        return len(self.__discs) == 0

    def populate_list_left(self, tracks, disc, pos):
        """
            Populate left list, thread safe
            @param tracks as [Track]
            @param disc as Disc
            @param pos as int
        """
        GLib.idle_add(self.__add_tracks,
                      tracks,
                      self._tracks_left,
                      disc.number,
                      pos)

    def populate_list_right(self, tracks, disc, pos):
        """
            Populate right list, thread safe
            @param tracks as [Track]
            @param disc as Disc
            @param pos as int
        """
        # If we are showing only one column, wait for widget1
        if self.__orientation == Gtk.Orientation.VERTICAL and\
           self.__locked_widget_right:
            GLib.timeout_add(100, self.populate_list_right, tracks, disc, pos)
        else:
            GLib.idle_add(self.__add_tracks,
                          tracks,
                          self._tracks_right,
                          disc.number,
                          pos)

    def get_current_ordinate(self, parent):
        """
            If current track in widget, return it ordinate,
            @param parent widget as Gtk.Widget
            @return y as int
        """
        for dic in [self._tracks_left, self._tracks_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    if child.id == Lp().player.current_track.id:
                        return child.translate_coordinates(parent, 0, 0)[1]
        return None

    def set_filter_func(self, func):
        """
            Set filter function
        """
        for widget in self._tracks_left.values():
            widget.set_filter_func(func)
        for widget in self._tracks_right.values():
            widget.set_filter_func(func)

    @property
    def boxes(self):
        """
            @return [Gtk.ListBox]
        """
        boxes = []
        for widget in self._tracks_left.values():
            boxes.append(widget)
        for widget in self._tracks_right.values():
            boxes.append(widget)
        return boxes

    @property
    def requested_height(self):
        """
            Requested height
        """
        if self.__requested_height < self.__height:
            return self.__height
        else:
            return self.__requested_height

#######################
# PROTECTED           #
#######################
    def _on_context_clicked(self, button):
        """
            Show context widget
            @param button as Gtk.Button
        """
        image = button.get_image()
        if self.__context is None:
            image.set_from_icon_name('go-previous-symbolic',
                                     Gtk.IconSize.MENU)
            self.__context = ContextWidget(self._album, button)
            self.__context.set_property('halign', Gtk.Align.START)
            self.__context.set_property('valign', Gtk.Align.CENTER)
            self.__context.show()
            self.__header.insert_next_to(button, Gtk.PositionType.RIGHT)
            self.__header.attach_next_to(self.__context, button,
                                         Gtk.PositionType.RIGHT, 1, 1)
        else:
            image.set_from_icon_name('go-next-symbolic',
                                     Gtk.IconSize.MENU)
            self.__context.destroy()
            self.__context = None

    def _on_album_updated(self, scanner, album_id, destroy):
        """
            On album modified, disable it
            @param scanner as CollectionScanner
            @param album id as int
            @param destroy as bool
        """
        if self._album.id != album_id:
            return
        removed = False
        for dic in [self._tracks_left, self._tracks_right]:
            for widget in dic.values():
                for child in widget.get_children():
                    track = Track(child.id)
                    if track.album.id == Type.NONE:
                        removed = True
        if removed:
            for dic in [self._tracks_left, self._tracks_right]:
                for widget in dic.values():
                    for child in widget.get_children():
                        child.destroy()
            self.__discs = self._album.discs
            self.__set_duration()
            self.populate()
        AlbumWidget._on_album_updated(self, scanner, album_id, destroy)

#######################
# PRIVATE             #
#######################
    def __set_duration(self):
        """
            Set album duration
        """
        duration = Lp().albums.get_duration(self._album.id,
                                            self._album.genre_ids)
        hours = int(duration / 3600)
        mins = int(duration / 60)
        if hours > 0:
            mins -= hours * 60
            if mins > 0:
                self.__duration_label.set_text(_("%s h  %s m") % (hours, mins))
            else:
                self.__duration_label.set_text(_("%s h") % hours)
        else:
            self.__duration_label.set_text(_("%s m") % mins)

    def __set_disc_height(self, disc):
        """
            Set disc widget height
            @param disc as Disc
        """
        count_tracks = len(disc.tracks)
        mid_tracks = int(0.5 + count_tracks / 2)
        left_height = self.__child_height * mid_tracks
        right_height = self.__child_height * (count_tracks - mid_tracks)
        if left_height > right_height:
            self.__requested_height += left_height
        else:
            self.__requested_height += right_height
        self._tracks_left[disc.number].set_property('height-request',
                                                    left_height)
        self._tracks_right[disc.number].set_property('height-request',
                                                     right_height)

    def __add_disc_container(self, disc_number):
        """
            Add disc container to box
            @param disc_number as int
        """
        self._tracks_left[disc_number] = TracksWidget()
        self._tracks_right[disc_number] = TracksWidget()
        self._tracks_left[disc_number].connect('activated',
                                               self.__on_activated)
        self._tracks_right[disc_number].connect('activated',
                                                self.__on_activated)
        self._tracks_left[disc_number].show()
        self._tracks_right[disc_number].show()

    def __pop_menu(self, widget):
        """
            Popup menu for album
            @param widget as Gtk.Button
            @param album id as int
        """
        ancestor = self.get_ancestor(Gtk.Popover)
        # Get album real genre ids (not contextual)
        genre_ids = Lp().albums.get_genre_ids(self._album.id)
        if genre_ids and genre_ids[0] == Type.CHARTS:
            popover = AlbumMenuPopover(self._album, None)
            popover.set_relative_to(widget)
            popover.set_position(Gtk.PositionType.BOTTOM)
        elif self._album.is_web:
            popover = AlbumMenuPopover(self._album,
                                       AlbumMenu(self._album,
                                                 ancestor is not None))
            popover.set_relative_to(widget)
        else:
            popover = Gtk.Popover.new_from_model(
                                            widget,
                                            AlbumMenu(self._album,
                                                      ancestor is not None))
        if ancestor is not None:
            Lp().window.view.show_popover(popover)
        else:
            popover.connect('closed', self.__on_pop_menu_closed)
            self.get_style_context().add_class('album-menu-selected')
            popover.show()

    def __add_tracks(self, tracks, widget, disc_number, i):
        """
            Add tracks for to tracks widget
            @param tracks as [int]
            @param widget as TracksWidget
            @param disc number as int
            @param i as int
        """
        if self._loading == Loading.STOP:
            self._loading = Loading.NONE
            return
        if not tracks:
            if widget == self._tracks_right:
                self._loading |= Loading.RIGHT
            elif widget == self._tracks_left:
                self._loading |= Loading.LEFT
            if self._loading == Loading.ALL:
                self.emit('populated')
            self.__locked_widget_right = False
            return

        track = tracks.pop(0)
        if not Lp().settings.get_value('show-tag-tracknumber'):
            track_number = i
        else:
            track_number = track.number

        row = TrackRow(track.id, track_number)
        row.show()
        widget[disc_number].add(row)
        GLib.idle_add(self.__add_tracks, tracks, widget, disc_number, i + 1)

    def __show_spinner(self, widget, track_id):
        """
            Show spinner for widget
            @param widget as TracksWidget
            @param track id as int
        """
        track = Track(track_id)
        if track.is_web:
            widget.show_spinner(track_id)

    def __on_size_allocate(self, widget, allocation):
        """
            Change box max/min children
            @param widget as Gtk.Widget
            @param allocation as Gtk.Allocation
        """
        if self.__width == allocation.width:
            return
        self.__width = allocation.width
        redraw = False
        # We want vertical orientation
        # when not enought place for cover or tracks
        if allocation.width < WindowSize.MEDIUM or (
                allocation.width < WindowSize.MONSTER and
                self._art_size == ArtSize.BIG):
            orientation = Gtk.Orientation.VERTICAL
        else:
            orientation = Gtk.Orientation.HORIZONTAL
        if orientation != self.__orientation:
            self.__orientation = orientation
            redraw = True

        if redraw:
            for child in self.__box.get_children():
                self.__box.remove(child)
            # Grid index
            idx = 0
            # Disc label width / right box position
            if orientation == Gtk.Orientation.VERTICAL:
                width = 1
                pos = 0
            else:
                width = 2
                pos = 1
            for disc in self._album.discs:
                show_label = len(self._album.discs) > 1
                if show_label:
                    label = Gtk.Label()
                    disc_text = _("Disc %s") % disc.number
                    disc_names = self._album.disc_names(disc.number)
                    if disc_names:
                        disc_text += ": " + ", ".join(disc_names)
                    label.set_text(disc_text)
                    label.set_property('halign', Gtk.Align.START)
                    label.get_style_context().add_class('dim-label')
                    label.show()
                    eventbox = Gtk.EventBox()
                    eventbox.add(label)
                    eventbox.connect('realize',
                                     self.__on_disc_label_realize)
                    eventbox.connect('button-press-event',
                                     self.__on_disc_press_event, disc.number)
                    eventbox.show()
                    self.__box.attach(eventbox, 0, idx, width, 1)
                    idx += 1
                GLib.idle_add(self.__box.attach,
                              self._tracks_left[disc.number],
                              0, idx, 1, 1)
                if orientation == Gtk.Orientation.VERTICAL:
                    idx += 1
                GLib.idle_add(self.__box.attach,
                              self._tracks_right[disc.number],
                              pos, idx, 1, 1)
                idx += 1
                GLib.idle_add(self.set_opacity, 1)
        if self._art_size == ArtSize.BIG:
            if allocation.width < WindowSize.MEDIUM:
                self.__coverbox.hide()
            else:
                self.__coverbox.show()

    def __on_disc_label_realize(self, eventbox):
        """
            Set mouse cursor
            @param eventbox as Gtk.EventBox
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def __on_disc_press_event(self, eventbox, event, idx):
        """
            Add/Remove disc to/from queue
            @param eventbox as Gtk.EventBox
            @param event as Gdk.Event
            @param idx as int
        """
        disc = None
        for d in self._album.discs:
            if d.number == idx:
                disc = d
                break
        if disc is None:
            return
        for track in disc.tracks:
            if Lp().player.track_in_queue(track):
                Lp().player.del_from_queue(track.id, False)
            else:
                Lp().player.append_to_queue(track.id, False)
        Lp().player.emit('queue-changed')

    def __on_pop_menu_closed(self, widget):
        """
            Remove selected style
            @param widget as Gtk.Popover
        """
        self.get_style_context().remove_class('album-menu-selected')

    def __on_activated(self, widget, track_id):
        """
            On track activation, play track
            @param widget as TracksWidget
            @param track id as int
        """
        # Add to queue by default
        if Lp().player.locked:
            if track_id in Lp().player.get_queue():
                Lp().player.del_from_queue(track_id)
            else:
                Lp().player.append_to_queue(track_id)
        else:
            # Do not update album list
            if not Lp().player.is_party and not\
                    Lp().settings.get_enum('playback') == NextContext.STOP:
                # If in artist view, reset album list
                if self._filter_ids:
                    Lp().player.set_albums(track_id,
                                           self._filter_ids,
                                           self._album.genre_ids)
                # Else, add album if missing
                elif not Lp().player.has_album(self._album):
                    Lp().player.add_album(self._album)
            # Clear albums if user clicked on a track from a new album
            elif Lp().settings.get_enum('playback') == NextContext.STOP:
                if not Lp().player.has_album(self._album):
                    Lp().player.clear_albums()
            self.__show_spinner(widget, track_id)
            track = Track(track_id)
            Lp().player.load(track)
