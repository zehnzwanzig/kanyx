import os
import sys
import re
import sqlite3
from pathlib import Path
from PySide6.QtCore import Qt, QMimeData, QPoint, QUrl, QRect, QEvent
from PySide6.QtGui import QDrag, QDesktopServices, QPixmap, QPainter, QColor, QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QMessageBox, QFileDialog, QScrollArea, QFrame, QCheckBox,
    QDateEdit, QSizePolicy, QInputDialog, QSizeGrip, QMenu, QStyledItemDelegate, QStackedWidget, QSlider, QFormLayout, QGroupBox)
from PySide6.QtCore import QDate
from i18n import LANGUAGES, PRIORITIES, tr
from version import __version__
from portability import export_workspace, stage_import, swap_in_workspace

STYLE = '''
* {font-family: 'Segoe UI', 'Inter', 'Arial'; font-size: 13px; color: #e7eaf0;}
QMainWindow, QWidget#root, QDialog {background: #171a21;}
/* 88 % opacity: wallpaper remains subtly visible through the columns. */
QFrame#lane {background-color: rgba(34, 38, 48, __LANE_ALPHA__); border: 1px solid rgba(75, 84, 101, 190); border-radius: 12px;}
/* Prevent the scroll area and its inner content from hiding the wallpaper. */
QScrollArea#cardScroll, QScrollArea#cardScroll > QWidget > QWidget {background: transparent; border: none;}
QPushButton#markdownToggle:checked {background: #5369ad; border: 1px solid #9aadf1; color: #ffffff; font-weight: 700;}
QPushButton#markdownToggle:checked:hover {background: #617cc0;}
QFrame#tile {background: #2b303b; border: 1px solid #3b424f; border-radius: 9px;}
QLineEdit, QTextEdit, QComboBox, QListWidget, QDateEdit {background: #242934; border: 1px solid #3a4150; border-radius: 7px; padding: 8px; selection-background-color: #6779c9;}
QLineEdit:focus, QTextEdit:focus, QListWidget:focus {border: 1px solid #8598ed;}
QPushButton {background: #343b49; border: 1px solid #424c5d; padding: 8px 12px; border-radius: 7px;}
QPushButton:hover {background: #455068;}
QPushButton#primary {background: #5369ad; border: 1px solid #647cca; font-weight: 600;}
QPushButton#primary:hover {background: #667dc5;}
QPushButton#danger {color: #f5a4a4;}
QLabel#subtle {color: #9aa3b7;}
QLabel#heading {font-size: 20px; font-weight: 700;}
QScrollArea {border: none; background: transparent;}
QScrollBar:horizontal, QScrollBar:vertical {background: #1c2028; height: 10px; width: 10px;}
QScrollBar::handle:horizontal, QScrollBar::handle:vertical {background: #495263; border-radius: 5px; min-height: 24px; min-width: 24px;}
QCheckBox {spacing: 8px;}
'''


# Values are stored per workspace and used to render CSS and wallpaper on demand.
DEFAULT_VISUALS = {'wallpaper_brightness': 39, 'column_opacity': 88, 'ui_scale': 100}
VISUAL_LIMITS = {'wallpaper_brightness': (0, 100), 'column_opacity': (45, 100), 'ui_scale': (80, 140)}

def visual_setting(store, name):
    low, high = VISUAL_LIMITS[name]
    try:
        return max(low, min(high, int(store.setting(name, str(DEFAULT_VISUALS[name])))))
    except (ValueError, TypeError):
        return DEFAULT_VISUALS[name]

def themed_style(opacity=88, scale=100):
    opacity = max(45, min(100, int(opacity)))
    scale = max(80, min(140, int(scale)))
    css = STYLE.replace('__LANE_ALPHA__', str(round(255 * opacity / 100)))
    # Scale all Qt pixel font sizes rather than overriding individual widgets.
    css = re.sub(r'font-size: (\d+)px', lambda m: 'font-size: %dpx' % round(int(m.group(1)) * scale / 100), css)
    return css


def button(text, callback, name=None):
    b = QPushButton(text)
    if name: b.setObjectName(name)
    b.clicked.connect(callback)
    return b


def ask(parent, title, label, default=''):
    value, ok = QInputDialog.getText(parent, title, label, text=default)
    return value.strip() if ok and value.strip() else None


class ChecklistEditDelegate(QStyledItemDelegate):
    """Keep inline checklist text legible across Windows Qt styles and themes."""
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setStyleSheet(
                'QLineEdit { color: #f4f6fc; background-color: #242934; '
                'border: 1px solid #8598ed; border-radius: 3px; '
                'selection-color: #ffffff; selection-background-color: #5369ad; '
                'padding: 2px 5px; }'
            )
        return editor


class WallpaperRoot(QWidget):
    """Cover-scaled background image with a dark overlay for readable UI."""
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setObjectName('root')
        self.background = QPixmap()
        self.brightness = visual_setting(store, 'wallpaper_brightness')
        self.reload_wallpaper()

    def reload_wallpaper(self):
        path = self.store.wallpaper_path()
        self.background = QPixmap(str(path)) if path and path.is_file() else QPixmap()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.background.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        size = self.background.size()
        scale = max(self.width() / size.width(), self.height() / size.height())
        sw, sh = int(size.width() * scale), int(size.height() * scale)
        rect = QRect((self.width() - sw) // 2, (self.height() - sh) // 2, sw, sh)
        painter.drawPixmap(rect, self.background)
        painter.fillRect(self.rect(), QColor(10, 13, 19, round(255 * (100 - self.brightness) / 100)))


class LaneDragHandle(QLabel):
    """Dragging the header moves the entire column, not its cards."""
    def __init__(self, column, text):
        super().__init__(text)
        self.column = column
        self.start = QPoint()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(column.window.t('Drag column left or right'))
        self.setAcceptDrops(True)
        self.setStyleSheet('font-weight: 700;')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self.start).manhattanLength() < QApplication.startDragDistance():
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData('application/x-kanyx-lane', str(self.column.lane['id']).encode('ascii'))
        drag.setMimeData(mime)
        # Match task dragging: show the actual column as a translucent ghost.
        preview = self.column.grab()
        if not preview.isNull():
            translucent = QPixmap(preview.size())
            translucent.fill(Qt.GlobalColor.transparent)
            painter = QPainter(translucent)
            painter.setOpacity(0.68)
            painter.drawPixmap(0, 0, preview)
            painter.end()
            drag.setPixmap(translucent)
            drag.setHotSpot(self.mapTo(self.column, self.start))
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-kanyx-lane'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-kanyx-lane'):
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.column.perform_lane_drop(event, self.mapTo(self.column, event.position().toPoint()).x())


class TitleBar(QFrame):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.drag_offset = None
        self.setFixedHeight(52)
        layout = QHBoxLayout(self)
        label = QLabel('◈  kanyx')
        label.setStyleSheet('font-size: 17px; font-weight: 800; color: #b2c0ff;')
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(button('—', window.showMinimized))
        layout.addWidget(button('□', self.toggle))
        layout.addWidget(button('✕', window.close))

    def toggle(self):
        self.window.showNormal() if self.window.isMaximized() else self.window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton) and not self.window.isMaximized():
            self.window.move(event.globalPosition().toPoint() - self.drag_offset)

    def mouseReleaseEvent(self, event):
        self.drag_offset = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()


class CardTile(QFrame):
    def __init__(self, store, card, open_card, drag_enabled=True):
        super().__init__()
        self.setObjectName('tile')
        self.cid = card['id']
        self.drag_enabled = drag_enabled
        self.start = QPoint()
        self.open_card = open_card
        v = QVBoxLayout(self)
        v.setSpacing(7)
        accent = card.get('color') or ''
        if accent:
            self.setStyleSheet('QFrame#tile { border-left: 4px solid %s; }' % accent)
        title = QLabel(card['title'])
        title.setWordWrap(True)
        title.setStyleSheet('font-weight: 600;')
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        v.addWidget(title)
        tags = store.card_tags(self.cid)
        checks = store.card_checks(self.cid)
        meta = []
        if card['priority'] != 'Normal':
            priority_key = next((key for key, value in PRIORITIES if value == card['priority']), card['priority'])
            meta.append('● '+open_card.__self__.t(priority_key))
        if card['due']: meta.append('◷ '+card['due'])
        if checks: meta.append(f"☑ {sum(bool(x['done']) for x in checks)}/{len(checks)}")
        if store.card_files(self.cid): meta.append('📎')
        if tags or meta:
            sub = QLabel('  ·  '.join(meta + ['#'+x for x in tags]))
            sub.setWordWrap(True)
            sub.setObjectName('subtle')
            sub.setStyleSheet('color: #aeb9d7; font-size: 11px;')
            sub.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            v.addWidget(sub)
        if checks:
            from PySide6.QtWidgets import QProgressBar
            progress = QProgressBar()
            progress.setRange(0, len(checks))
            progress.setValue(sum(bool(x['done']) for x in checks))
            progress.setTextVisible(False)
            progress.setFixedHeight(5)
            progress.setStyleSheet('QProgressBar {background:#181e28; border:0; border-radius:2px;} QProgressBar::chunk {background:#6cbbab; border-radius:2px;}')
            v.addWidget(progress)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if not self.drag_enabled or not (event.buttons() & Qt.MouseButton.LeftButton): return
        if (event.position().toPoint()-self.start).manhattanLength() < QApplication.startDragDistance(): return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData('application/x-kanyx-card', str(self.cid).encode())
        drag.setMimeData(mime)
        # Render the complete card as a translucent drag image that follows
        # the pointer. Qt manages movement and DPI scaling on both platforms.
        preview = self.grab()
        if not preview.isNull():
            translucent = QPixmap(preview.size())
            translucent.fill(Qt.GlobalColor.transparent)
            painter = QPainter(translucent)
            painter.setOpacity(0.68)
            painter.drawPixmap(0, 0, preview)
            painter.end()
            drag.setPixmap(translucent)
            drag.setHotSpot(event.position().toPoint())
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and (event.position().toPoint()-self.start).manhattanLength() < QApplication.startDragDistance():
            self.open_card(self.cid)


class CardScroll(QScrollArea):
    def __init__(self, column):
        super().__init__()
        self.column = column
        self.setObjectName('cardScroll')
        self.setStyleSheet('QScrollArea#cardScroll { background: transparent; }')
        self.viewport().setAutoFillBackground(False)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.viewport():
            t = event.type()
            from PySide6.QtCore import QEvent
            if t in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if event.mimeData().hasFormat('application/x-kanyx-card') or event.mimeData().hasFormat('application/x-kanyx-lane'):
                    event.acceptProposedAction()
                    return True
            if t == QEvent.Type.Drop:
                pos = self.viewport().mapTo(self.column, event.position().toPoint())
                if event.mimeData().hasFormat('application/x-kanyx-card'):
                    self.column.perform_drop(event, pos.y())
                    return True
                if event.mimeData().hasFormat('application/x-kanyx-lane'):
                    self.column.perform_lane_drop(event, pos.x())
                    return True
        return super().eventFilter(watched, event)


class DropColumn(QFrame):
    def __init__(self, window, lane, cards):
        super().__init__()
        self.window = window
        self.lane = lane
        self.setObjectName('lane')
        self.setAcceptDrops(True)
        self.setFixedWidth(58 if lane.get('collapsed') else 300)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        head = QHBoxLayout()
        name = LaneDragHandle(self, f"⠿  {lane['title']}  {len(cards)}")
        if not lane.get('collapsed'):
            head.addWidget(name)
        else:
            name.deleteLater()
            compact = QLabel('▸')
            compact.setToolTip(lane['title'])
            head.addWidget(compact)
        head.addStretch()
        head.addWidget(button('›' if lane.get('collapsed') else '‹', self.toggle_collapse))
        if not lane.get('collapsed'):
            head.addWidget(button('⋯', self.manage))
        outer.addLayout(head)
        area = CardScroll(self)
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        content.setAutoFillBackground(False)
        content.setAcceptDrops(False)
        self.cards_layout = QVBoxLayout(content)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setSpacing(9)
        self.card_widgets = []
        for card in cards:
            tile = CardTile(window.store, card, window.edit_card)
            self.cards_layout.addWidget(tile)
            self.card_widgets.append(tile)
        self.cards_layout.addStretch()
        area.setWidget(content)
        if not lane.get('collapsed'):
            outer.addWidget(area)
            outer.addWidget(button('＋ ' + window.t('Add task'), self.add_card))
        else:
            area.deleteLater()
            vertical = QLabel(lane['title'] + ' (' + str(len(cards)) + ')')
            vertical.setWordWrap(True)
            vertical.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vertical.setToolTip(lane['title'])
            outer.addWidget(vertical, 1)
        self.setMinimumHeight(400)

    def toggle_collapse(self):
        self.window.store.set_lane_collapsed(self.lane['id'], not self.lane.get('collapsed'))
        self.window.refresh()

    def add_card(self):
        title = ask(self, self.window.t('New task'), self.window.t('Task title:'))
        if title:
            # No database insert before the editor is accepted.
            CardDialog(self.window, None, is_new=True, lane_id=self.lane['id'], initial_title=title).exec()
            self.window.refresh()

    def manage(self):
        choices = [self.window.t(k) for k in ('Rename', 'Move left', 'Move right', 'Delete column')]
        choice, ok = QInputDialog.getItem(self, self.window.t('Manage column'), self.window.t('Action:'), choices, 0, False)
        if not ok: return
        if choice == choices[0]:
            title = ask(self, self.window.t('Rename'), self.window.t('Column name:'), self.lane['title'])
            if title: self.window.change_with_undo(lambda: self.window.store.rename_lane(self.lane['id'],title), lambda: self.window.store.rename_lane(self.lane['id'],self.lane['title']))
        elif choice in choices[1:3]:
            lanes = self.window.store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (self.lane['board_id'],))
            current = next(i for i, lane in enumerate(lanes) if lane['id'] == self.lane['id'])
            destination = current + (-1 if choice == choices[1] else 1)
            self.window.change_with_undo(lambda: self.window.store.move_lane(self.lane['id'],destination), lambda: self.window.store.move_lane(self.lane['id'],current))
        elif choice == choices[3] and QMessageBox.question(self,self.window.t('Delete column'),self.window.t('Delete this column and all its tasks permanently?')) == QMessageBox.StandardButton.Yes:
            self.window.store.delete_lane(self.lane['id'])
        self.window.refresh()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-kanyx-card') or event.mimeData().hasFormat('application/x-kanyx-lane'): event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-kanyx-card') or event.mimeData().hasFormat('application/x-kanyx-lane'): event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat('application/x-kanyx-lane'):
            self.perform_lane_drop(event, event.position().x())
        else:
            self.perform_drop(event, event.position().toPoint().y())

    def perform_lane_drop(self, event, x):
        if event.mimeData().hasFormat('application/x-kanyx-lane'):
            try:
                moving_id = int(bytes(event.mimeData().data('application/x-kanyx-lane')).decode('ascii'))
            except ValueError:
                return
            moving = self.window.store.one('SELECT board_id FROM lanes WHERE id=?', (moving_id,))
            if not moving or moving['board_id'] != self.lane['board_id']:
                return
            lanes = self.window.store.rows('SELECT id FROM lanes WHERE board_id=? ORDER BY position,id', (self.lane['board_id'],))
            ordered = [row['id'] for row in lanes if row['id'] != moving_id]
            if self.lane['id'] == moving_id:
                event.acceptProposedAction()
                return
            target_index = ordered.index(self.lane['id'])
            if x >= self.width() / 2:
                target_index += 1
            previous = next(i for i, x in enumerate(lanes) if x['id'] == moving_id)
            self.window.change_with_undo(lambda: self.window.store.move_lane(moving_id,target_index), lambda: self.window.store.move_lane(moving_id,previous))
            event.acceptProposedAction()
            self.window.refresh()
            return

    def perform_drop(self, event, y):
        if not event.mimeData().hasFormat('application/x-kanyx-card'): return
        try: cid = int(bytes(event.mimeData().data('application/x-kanyx-card')).decode())
        except ValueError: return
        positions = [tile.mapTo(self, QPoint(0, tile.height()//2)).y() for tile in self.card_widgets if tile.cid != cid]
        index = sum(y > pos for pos in positions)
        current = self.window.store.card(cid)
        previous_lane, previous_position = current['lane_id'], current['position']
        self.window.change_with_undo(lambda: self.window.store.move_card(cid,self.lane['id'],index),
                                     lambda: self.window.store.move_card(cid,previous_lane,previous_position))
        event.acceptProposedAction()
        self.window.refresh()


class CardDialog(QDialog):
    def __init__(self, window, cid, is_new=False, lane_id=None, initial_title=''):
        super().__init__(window)
        self.window = window
        self.store = window.store
        self.cid = cid
        self.is_new = is_new
        self.lane_id = lane_id
        self.pending_removed_ids = set()
        self.pending_added_paths = []
        if is_new:
            if lane_id is None:
                raise ValueError('New task requires a target column')
            card = {'title': initial_title, 'description': '', 'priority': 'Normal',
                    'due': '', 'color': ''}
        else:
            card = self.store.card(cid)
            if card is None:
                raise ValueError('Task does not exist')
        self.setWindowTitle(window.t('New task') if is_new else window.t('Edit task'))
        # At Windows 125/150% DPI (or on smaller displays), the editor must
        # scroll its fields instead of hiding Save and Cancel off-screen.
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        self.resize(min(590, max(400, available.width() - 60)) if available else 590,
                    min(720, max(350, available.height() - 80)) if available else 720)
        dialog_layout = QVBoxLayout(self)
        fields_scroll = QScrollArea(self)
        fields_scroll.setWidgetResizable(True)
        fields_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        fields_scroll.setFrameShape(QFrame.Shape.NoFrame)
        fields = QWidget()
        root = QVBoxLayout(fields)
        fields_scroll.setWidget(fields)
        dialog_layout.addWidget(fields_scroll, 1)
        self.title = QLineEdit(card['title'])
        root.addWidget(QLabel(window.t('Title')))
        root.addWidget(self.title)
        root.addWidget(QLabel(window.t('Description')))
        # QTextEdit(text) parses HTML automatically; preserve the source verbatim.
        self.desc = QTextEdit()
        self.desc.setAcceptRichText(False)
        self.desc.setPlainText(card['description'] or '')
        self.desc.setMaximumHeight(120)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(120)
        self.preview.setVisible(False)
        self.markdown_toggle = QPushButton(window.t('Toggle Markdown preview'))
        self.markdown_toggle.setObjectName('markdownToggle')
        self.markdown_toggle.setCheckable(True)
        self.markdown_toggle.setToolTip(window.t('Toggle Markdown preview'))
        def toggle_markdown(showing):
            if showing:
                self.preview.setMarkdown(self.desc.toPlainText())
            self.preview.setVisible(showing)
            self.desc.setVisible(not showing)
            if not showing:
                self.desc.setFocus()
        self.markdown_toggle.toggled.connect(toggle_markdown)
        root.addWidget(self.markdown_toggle)
        root.addWidget(self.desc)
        root.addWidget(self.preview)
        line = QHBoxLayout()
        self.priority = QComboBox()
        
        for key, value in PRIORITIES: self.priority.addItem(window.t(key), value)
        self.priority.setCurrentIndex(max(0, self.priority.findData(card['priority'])))
        line.addWidget(QLabel(window.t('Priority')))
        line.addWidget(self.priority)
        self.due = QDateEdit()
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat('yyyy-MM-dd')
        self.due.setDate(QDate.fromString(card['due'],'yyyy-MM-dd') if card['due'] else QDate.currentDate())
        self.has_due = QCheckBox(window.t('Due date'))
        self.has_due.setChecked(bool(card['due']))
        line.addWidget(self.has_due)
        line.addWidget(self.due)
        root.addLayout(line)
        colors = QHBoxLayout()
        colors.addWidget(QLabel(window.t('Card color')))
        self.card_color = QComboBox()
        for label, value in [('No color',''),('Blue','#4f98c8'),('Green','#6bb6a4'),('Amber','#d7a15a'),('Rose','#c97893'),('Purple','#9a8dd2')]:
            # A visual swatch in the closed selector and in the drop-down list.
            swatch = QPixmap(22, 16)
            swatch.fill(QColor(value) if value else QColor('#343b49'))
            self.card_color.addItem(QIcon(swatch), window.t(label), value)
            idx = self.card_color.count() - 1
            if value:
                self.card_color.setItemData(idx, QColor(value).darker(260), Qt.ItemDataRole.BackgroundRole)
                self.card_color.setItemData(idx, QColor('#ffffff'), Qt.ItemDataRole.ForegroundRole)
        self.card_color.setCurrentIndex(max(0,self.card_color.findData(card.get('color',''))))
        colors.addWidget(self.card_color)
        root.addLayout(colors)
        root.addWidget(QLabel(window.t('Tags (comma-separated)')))
        self.tags = QLineEdit(', '.join(self.store.card_tags(cid)) if not is_new else '')
        root.addWidget(self.tags)
        root.addWidget(QLabel(window.t('Checklist (double-click to edit, check to complete)')))
        self.checks = QListWidget()
        self.checks.setItemDelegate(ChecklistEditDelegate(self.checks))
        self.checks.setMaximumHeight(150)
        for row in (self.store.card_checks(cid) if not is_new else []): self.add_check(row['body'],bool(row['done']))
        root.addWidget(self.checks)
        cline = QHBoxLayout()
        cline.addWidget(button('＋ ' + window.t('Add checklist item'), lambda: self.add_check(window.t('New item'))))
        cline.addWidget(button('− ' + window.t('Remove'), lambda: self.checks.takeItem(self.checks.currentRow())))
        root.addLayout(cline)
        root.addWidget(QLabel(window.t('Attachments (stored in data folder)')))
        self.files = QListWidget()
        self.files.setMaximumHeight(100)
        self.files.itemDoubleClicked.connect(self.open_file)
        root.addWidget(self.files)
        fline = QHBoxLayout()
        fline.addWidget(button('＋ ' + window.t('Attach file'), self.attach))
        fline.addWidget(button('− ' + window.t('Remove attachment'), self.remove_file))
        root.addLayout(fline)
        self.load_files()
        actions = QHBoxLayout()
        if not is_new:
            actions.addWidget(button(window.t('Archive'), self.archive))
            actions.addWidget(button(window.t('Duplicate'), self.duplicate))
            actions.addWidget(button(window.t('Delete task'), self.delete, 'danger'))
        actions.addStretch()
        actions.addWidget(button(window.t('Cancel'), self.reject))
        actions.addWidget(button(window.t('Save'), self.save, 'primary'))
        dialog_layout.addLayout(actions)
        # Existing cards open in formatted preview; new cards open ready for typing.
        # The editable source in self.desc is never replaced by rendered Markdown.
        self.markdown_toggle.setChecked(not is_new)

    def add_check(self, text, checked=False):
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.checks.addItem(item)

    def load_files(self):
        self.files.clear()
        if not self.is_new:
            for row in self.store.card_files(self.cid):
                if row['id'] in self.pending_removed_ids:
                    continue
                item = QListWidgetItem(row['original_name'])
                item.setData(Qt.ItemDataRole.UserRole, {'stored': row})
                self.files.addItem(item)
        for index, path in enumerate(self.pending_added_paths):
            item = QListWidgetItem('＋ ' + path.name)
            item.setData(Qt.ItemDataRole.UserRole, {'pending_index': index})
            self.files.addItem(item)

    def attach(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.window.t('Choose attachments'))
        # Stage additions: Cancel must never copy files into the workspace.
        for path in paths:
            candidate = Path(path)
            if candidate.is_file():
                self.pending_added_paths.append(candidate)
            else:
                QMessageBox.warning(self, self.window.t('File error'), str(candidate))
        self.load_files()

    def remove_file(self):
        item = self.files.currentItem()
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if 'pending_index' in data:
            self.pending_added_paths.pop(data['pending_index'])
        else:
            # Stage deletions: the file and database record survive Cancel.
            self.pending_removed_ids.add(data['stored']['id'])
        self.load_files()

    def open_file(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if 'pending_index' in data:
            path = self.pending_added_paths[data['pending_index']]
        else:
            path = self.store.attachments / data['stored']['stored_name']
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def save(self):
        title = self.title.text().strip()
        if not title:
            QMessageBox.warning(self,self.window.t('Missing title'),self.window.t('Task needs a title.'))
            return
        checks = [(self.checks.item(i).text(), self.checks.item(i).checkState() == Qt.CheckState.Checked) for i in range(self.checks.count())]
        new_cid = None
        added_ids = []
        try:
            if self.is_new:
                new_cid = self.store.add_card(self.lane_id, title)
                self.cid = new_cid
            self.store.update_card(self.cid, title, self.desc.toPlainText(), self.priority.currentData(),
                self.due.date().toString('yyyy-MM-dd') if self.has_due.isChecked() else '',
                self.tags.text(), checks, self.card_color.currentData())
            for path in self.pending_added_paths:
                added_ids.append(self.store.add_file(self.cid, path))
            for file_id in self.pending_removed_ids:
                self.store.delete_file(file_id)
        except (OSError, ValueError, sqlite3.Error) as exc:
            for file_id in added_ids:
                self.store.delete_file(file_id)
            if new_cid is not None:
                self.store.delete_card(new_cid)
                self.cid = None
            QMessageBox.warning(self, self.window.t('File error'), str(exc))
            return
        self.accept()

    def archive(self):
        cid = self.cid
        self.window.change_with_undo(lambda: self.store.archive_card(cid,True),lambda: self.store.archive_card(cid,False))
        self.accept()

    def duplicate(self):
        original_id = self.cid
        created = [None]
        def forward():
            created[0] = self.store.duplicate_card(original_id)
        def reverse():
            if created[0] is not None:
                self.store.delete_card(created[0])
        self.window.change_with_undo(forward,reverse)
        self.accept()

    def delete(self):
        if QMessageBox.question(self,self.window.t('Delete'),self.window.t('Delete this task permanently?')) == QMessageBox.StandardButton.Yes:
            self.store.delete_card(self.cid)
            self.accept()


class MainWindow(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.language = store.setting('language', 'en')
        if self.language not in LANGUAGES: self.language = 'en'
        self.setWindowTitle(f'Kanyx {__version__}')
        asset_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets'
        icon_path = asset_dir / 'kanyx.png'
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.resize(1200, 780)
        self.setMinimumSize(780, 540)
        self.resize_margin = 7
        self.drag_edge = None
        self.history = []
        self.future = []
        self.build_interface()
        self.apply_visual_settings()
        QShortcut(QKeySequence('Ctrl+Z'),self,activated=self.undo)
        QShortcut(QKeySequence('Ctrl+Shift+Z'),self,activated=self.redo)
        QShortcut(QKeySequence('Ctrl+Y'),self,activated=self.redo)
        QShortcut(QKeySequence('Ctrl+F'),self,activated=self.search.setFocus)
        QShortcut(QKeySequence('Ctrl+N'),self,activated=self.add_lane)
        QShortcut(QKeySequence('Ctrl+Shift+N'),self,activated=self.add_board)
        QShortcut(QKeySequence('Ctrl+L'),self,activated=self.search.setFocus)
        QShortcut(QKeySequence('Escape'),self,activated=self.clear_filters)
        QShortcut(QKeySequence('Ctrl+1'),self,activated=lambda: self.select_board_index(0))
        QShortcut(QKeySequence('Ctrl+2'),self,activated=lambda: self.select_board_index(1))
        QShortcut(QKeySequence('Ctrl+3'),self,activated=lambda: self.select_board_index(2))


    def build_interface(self, preferred_board=None, search_term='', priority_code='Alle'):
        store = self.store
        root = WallpaperRoot(store)
        self.setCentralWidget(root)
        stack = QVBoxLayout(root)
        stack.setContentsMargins(12, 4, 12, 12)
        stack.addWidget(TitleBar(self))
        # Keep controls legible at high display/UI scaling. Actions scroll
        # horizontally when the window is narrow; search stays on a second row.
        toolbar_content = QWidget()
        top = QHBoxLayout(toolbar_content)
        top.setContentsMargins(0, 0, 0, 0)
        self.board_select = QComboBox()
        self.board_select.setMinimumWidth(190)
        self.board_select.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.board_select)
        top.addWidget(button('＋ ' + self.t('New board'), self.add_board))
        top.addWidget(button(self.t('Templates'), self.new_from_template))
        top.addWidget(button('⋯ ' + self.t('Manage board'), self.manage_board))
        top.addWidget(button('▣ ' + self.t('Archive'), self.show_archive))
        top.addWidget(button('↶', self.undo))
        top.addWidget(button('↷', self.redo))
        top.addWidget(button('▧ ' + self.t('Wallpaper'), self.manage_wallpaper))
        top.addWidget(button('⚙ ' + self.t('Appearance'), self.open_appearance))
        data_btn = QPushButton('⋯ ' + self.t('Workspace'))
        data_menu = QMenu(data_btn)
        data_menu.addAction(self.t('Export workspace…'), self.export_workspace)
        data_menu.addAction(self.t('Import workspace…'), self.import_workspace)
        data_menu.addSeparator()
        data_menu.addAction(self.t('Create database backup'), self.create_backup)
        data_menu.addAction(self.t('Check data integrity'), self.check_integrity)
        data_btn.setMenu(data_menu)
        top.addWidget(data_btn)
        toolbar_content.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        toolbar_content.adjustSize()
        tools_scroll = QScrollArea()
        tools_scroll.setObjectName('toolsScroll')
        tools_scroll.setWidgetResizable(False)
        tools_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tools_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tools_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tools_scroll.setWidget(toolbar_content)
        self.toolbar_content = toolbar_content
        self.tools_scroll = tools_scroll
        stack.addWidget(tools_scroll)
        filters = QHBoxLayout()
        filters.addWidget(QLabel(self.t('Language') + ':'))
        self.language_select = QComboBox()
        for code, name in LANGUAGES.items():
            self.language_select.addItem(name, code)
        self.language_select.setCurrentIndex(self.language_select.findData(self.language))
        self.language_select.currentIndexChanged.connect(self.change_language)
        filters.addWidget(self.language_select)
        self.search = QLineEdit()
        self.search.setMinimumWidth(120)
        self.search.setPlaceholderText(self.t('Search tasks, descriptions and tags…'))
        self.search.textChanged.connect(self.refresh)
        filters.addWidget(self.search,1)
        self.priority = QComboBox()
        self.priority.addItem(self.t('All'), 'Alle')
        for key, value in PRIORITIES: self.priority.addItem(self.t(key), value)
        self.priority.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.priority)
        stack.addLayout(filters)
        sub = QHBoxLayout()
        self.heading = QLabel(self.t('My board'))
        self.heading.setObjectName('heading')
        self.heading.setMinimumWidth(0)
        self.heading.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        sub.addWidget(self.heading, 1)
        sub.addStretch()
        sub.addWidget(button('＋ ' + self.t('New column'), self.add_lane,'primary'))
        stack.addLayout(sub)
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet('QScrollArea { background: transparent; }')
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.setWidgetResizable(True)
        stack.addWidget(self.scroll,1)
        self.status = QLabel()
        self.status.setObjectName('subtle')
        self.status.setMinimumWidth(0)
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        footer = QHBoxLayout()
        footer.addWidget(self.status, 1)
        grip = QSizeGrip(root)
        footer.addWidget(grip)
        stack.addLayout(footer)
        self.search.setText(search_term)
        self.priority.setCurrentIndex(max(0, self.priority.findData(priority_code)))
        self.load_boards(preferred_board)
        self.resize_toolbar_to_contents()

    def resize_toolbar_to_contents(self):
        # Qt style sheets can resize the buttons as interface-scale changes.
        # Always allow enough vertical room for a horizontal scrollbar.
        if hasattr(self, 'toolbar_content'):
            self.toolbar_content.adjustSize()
            bar = self.tools_scroll.horizontalScrollBar()
            self.tools_scroll.setFixedHeight(
                self.toolbar_content.sizeHint().height() + bar.sizeHint().height() + 6)

    def t(self, key):
        return tr(self.language, key)

    def export_workspace(self):
        path, _ = QFileDialog.getSaveFileName(self, self.t('Export workspace…'),
            str(self.store.root / 'Kanyx-workspace.kanyx'), 'Kanyx Workspace (*.kanyx)')
        if not path: return
        try:
            output = export_workspace(self.store, path)
            QMessageBox.information(self, self.t('Workspace'),
                self.t('Workspace exported successfully.') + '\n' + str(output))
        except Exception as exc:
            QMessageBox.critical(self, self.t('Export failed'), str(exc))

    def import_workspace(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t('Import workspace…'),
            str(self.store.root), 'Kanyx Workspace (*.kanyx)')
        if not path: return
        answer = QMessageBox.warning(self, self.t('Import workspace…'),
            self.t('Import replaces the current workspace. The previous data folder will be kept as a backup. Continue?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes: return
        staged = None
        try:
            staged = stage_import(path, self.store.root)
            previous = swap_in_workspace(self.store, staged)
            staged = None
            self.history.clear()
            self.future.clear()
            self.build_interface()
            self.apply_visual_settings()
            QMessageBox.information(self, self.t('Workspace'),
                self.t('Workspace imported successfully.') + '\n' +
                self.t('Previous workspace saved at:') + '\n' + str(previous))
        except Exception as exc:
            QMessageBox.critical(self, self.t('Import failed'), str(exc))
        finally:
            if staged is not None:
                import shutil
                shutil.rmtree(staged, ignore_errors=True)

    def create_backup(self):
        try:
            result = self.store.backup_now()
            QMessageBox.information(self, self.t('Workspace'),
                self.t('Database backup created.') + '\n' + str(result))
        except Exception as exc:
            QMessageBox.critical(self, self.t('Backup failed'), str(exc))

    def check_integrity(self):
        try:
            missing = self.store.verify_integrity()
            if missing:
                QMessageBox.warning(self, self.t('Workspace'),
                    self.t('Missing attached files:') + '\n' + '\n'.join(missing[:30]))
            else:
                QMessageBox.information(self, self.t('Workspace'), self.t('Data integrity verified.'))
        except Exception as exc:
            QMessageBox.critical(self, self.t('Integrity check failed'), str(exc))

    def change_language(self, *_):
        code = self.language_select.currentData()
        if not code or code == self.language:
            return
        selected_board = self.board_id()
        search_term = self.search.text()
        priority_code = self.priority.currentData()
        self.language = code
        self.store.set_setting('language', code)
        # Rebuild only the UI: database and user-generated titles remain untouched.
        old = self.takeCentralWidget()
        # Reuse initialization for consistent translations across all controls.
        old.deleteLater()
        self.build_interface(selected_board, search_term, priority_code)

    def load_boards(self, preferred=None):
        self.board_select.blockSignals(True)
        existing = preferred if preferred is not None else self.board_select.currentData()
        self.board_select.clear()
        for board in self.store.rows('SELECT * FROM boards ORDER BY position,id'):
            self.board_select.addItem(board['title'],board['id'])
        index = self.board_select.findData(existing)
        self.board_select.setCurrentIndex(max(0,index))
        self.board_select.blockSignals(False)
        self.refresh()

    def board_id(self):
        return self.board_select.currentData()

    def refresh(self, *_):
        bid = self.board_id()
        if bid is None: return
        board = self.store.one('SELECT * FROM boards WHERE id=?',(bid,))
        if not board: return
        self.heading.setText(board['title'])
        container = QWidget()
        container.setObjectName('boardSurface')
        container.setStyleSheet('QWidget#boardSurface { background: transparent; }')
        columns = QHBoxLayout(container)
        columns.setContentsMargins(2, 8, 8, 8)
        columns.setSpacing(14)
        cards = self.store.search_cards(bid,self.search.text().strip(),self.priority.currentData())
        lanes = self.store.rows('SELECT * FROM lanes WHERE board_id=? ORDER BY position,id',(bid,))
        for lane in lanes:
            columns.addWidget(DropColumn(self,lane,[card for card in cards if card['lane_id']==lane['id']]))
        columns.addStretch()
        self.scroll.setWidget(container)
        status = f"{len(cards)} {self.t('tasks')} · {len(lanes)} {self.t('columns')} · {self.t('Offline')} · {self.t('Data')}: {self.store.dbfile}"
        self.status.setText(status)
        self.status.setToolTip(status)

    def change_with_undo(self, forward, backwards):
        forward()
        self.history.append((forward,backwards))
        if len(self.history)>50: self.history.pop(0)
        self.future.clear()

    def undo(self):
        if not self.history: return
        command = self.history.pop()
        command[1]()
        self.future.append(command)
        self.refresh()

    def redo(self):
        if not self.future: return
        command = self.future.pop()
        command[0]()
        self.history.append(command)
        self.refresh()

    def show_archive(self):
        bid = self.board_id()
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t('Archive'))
        dialog.resize(580,420)
        layout = QVBoxLayout(dialog)
        listing = QListWidget()
        def populate():
            listing.clear()
            for card in self.store.archived_cards(bid):
                item = QListWidgetItem(f"{card['title']}  —  {card['lane_title']}")
                item.setData(Qt.ItemDataRole.UserRole,card['id'])
                listing.addItem(item)
        populate()
        layout.addWidget(listing)
        def restore():
            item = listing.currentItem()
            if not item: return
            cid = item.data(Qt.ItemDataRole.UserRole)
            self.change_with_undo(lambda: self.store.archive_card(cid,False),lambda: self.store.archive_card(cid,True))
            populate()
            self.refresh()
        layout.addWidget(button(self.t('Restore'),restore))
        layout.addWidget(button(self.t('Close'),dialog.accept))
        dialog.exec()

    def apply_visual_settings(self, settings=None):
        values = settings or {key: visual_setting(self.store, key) for key in DEFAULT_VISUALS}
        QApplication.instance().setStyleSheet(themed_style(values['column_opacity'], values['ui_scale']))
        self.resize_toolbar_to_contents()
        root = self.centralWidget()
        if isinstance(root, WallpaperRoot):
            root.brightness = values['wallpaper_brightness']
            root.update()

    def open_appearance(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t('Appearance'))
        dialog.setMinimumWidth(385)
        layout = QVBoxLayout(dialog)
        description = QLabel(self.t('Changes are previewed immediately. Cancel restores the previous settings.'))
        description.setWordWrap(True)
        layout.addWidget(description)
        original = {name: visual_setting(self.store, name) for name in DEFAULT_VISUALS}
        current = original.copy()
        sliders = {}
        for key, caption, suffix in (
                ('wallpaper_brightness', self.t('Wallpaper brightness'), '%'),
                ('column_opacity', self.t('Column opacity'), '%'),
                ('ui_scale', self.t('Interface scale'), '%')):
            row = QHBoxLayout()
            label = QLabel(caption)
            label.setMinimumWidth(148)
            slider = QSlider(Qt.Orientation.Horizontal)
            low, high = VISUAL_LIMITS[key]
            slider.setRange(low, high)
            slider.setSingleStep(1 if key != 'ui_scale' else 5)
            slider.setValue(current[key])
            sliders[key] = slider
            value = QLabel(f'{current[key]}{suffix}')
            value.setMinimumWidth(46)
            def changed(n, key=key, value=value, suffix=suffix):
                current[key] = n
                value.setText(f'{n}{suffix}')
                self.apply_visual_settings(current)
            slider.valueChanged.connect(changed)
            row.addWidget(label)
            row.addWidget(slider, 1)
            row.addWidget(value)
            layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.RestoreDefaults)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        def restore_defaults():
            for key, slider in sliders.items():
                slider.setValue(DEFAULT_VISUALS[key])
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(restore_defaults)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for key, value in current.items():
                self.store.set_setting(key, str(value))
        else:
            self.apply_visual_settings(original)

    def manage_wallpaper(self):
        choice, ok = QInputDialog.getItem(
            self, self.t('Wallpaper'), self.t('Wallpaper') + ':',
            [self.t('Choose image…'), self.t('Remove wallpaper')], 0, False)
        if not ok:
            return
        if choice == self.t('Choose image…'):
            path, _ = QFileDialog.getOpenFileName(
                self, self.t('Select wallpaper'), '', self.t('Images') + ' (*.png *.jpg *.jpeg *.webp *.bmp)')
            if not path:
                return
            preview = QPixmap(path)
            if preview.isNull():
                QMessageBox.warning(self, self.t('Image error'), self.t('Unable to load this image.'))
                return
            try:
                self.store.set_wallpaper(path)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, self.t('Image error'), str(exc))
                return
        else:
            self.store.clear_wallpaper()
        self.centralWidget().reload_wallpaper()

    def clear_filters(self):
        self.search.clear()
        self.priority.setCurrentIndex(0)

    def select_board_index(self, index):
        if index < self.board_select.count():
            self.board_select.setCurrentIndex(index)

    def new_from_template(self):
        options = [('Simple','simple'), ('Project','project'), ('Personal','personal'), ('Blank','blank')]
        selected, ok = QInputDialog.getItem(self, self.t('Templates'), self.t('Select template:'),
                                            [self.t(label) for label,_ in options], 0, False)
        if not ok: return
        index = next((i for i,(label,_) in enumerate(options) if self.t(label)==selected), 0)
        title = ask(self,self.t('Create board'),self.t('Board name:'))
        if not title: return
        bid = self.store.create_board_from_template(title,options[index][1])
        self.load_boards(bid)

    def add_board(self):
        title = ask(self,self.t('Create board'),self.t('Board name:'))
        if title:
            bid = self.store.add_board(title)
            for lane in ('To Do','In Progress','Done'): self.store.add_lane(bid,lane)
            self.load_boards(bid)

    def manage_board(self):
        bid = self.board_id()
        choice, ok = QInputDialog.getItem(self,self.t('Manage board'),self.t('Action:'),[self.t('Rename'),self.t('Duplicate board'),self.t('Delete board')],0,False)
        if not ok: return
        if choice == self.t('Rename'):
            title = ask(self,self.t('Rename board'),self.t('Name:'),self.board_select.currentText())
            if title:
                old_name = self.board_select.currentText()
                self.change_with_undo(lambda: self.store.rename_board(bid,title),lambda: self.store.rename_board(bid,old_name))
        elif choice == self.t('Duplicate board'):
            created = [None]
            def forward():
                created[0] = self.store.duplicate_board(bid)
            def reverse():
                if created[0] is not None:
                    self.store.delete_board(created[0])
            self.change_with_undo(forward,reverse)
            self.load_boards(created[0])
            return
        elif QMessageBox.question(self,self.t('Delete board'),self.t('Delete this board and all tasks permanently?')) == QMessageBox.StandardButton.Yes:
            self.store.delete_board(bid)
            if not self.store.rows('SELECT id FROM boards'): self.store.add_board(self.t('My board'))
        self.load_boards()

    def add_lane(self):
        title = ask(self,self.t('New column'),self.t('Column name:'))
        if title:
            self.store.add_lane(self.board_id(),title)
            self.refresh()

    def edit_card(self, cid, is_new=False):
        result = CardDialog(self, cid, is_new=is_new).exec()
        self.refresh()
        return result

    def closeEvent(self, event):
        self.store.close()
        super().closeEvent(event)

    def nativeEvent(self, eventType, message):
        # Native window snapping / edges may differ across operating systems.
        return super().nativeEvent(eventType,message)


def run(store):
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(themed_style(visual_setting(store, 'column_opacity'), visual_setting(store, 'ui_scale')))
    window = MainWindow(store)
    window.show()
    return app.exec()
