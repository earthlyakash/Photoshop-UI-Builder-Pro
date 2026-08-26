import sys
import json
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QFrame,
                             QScrollArea, QMessageBox, QGridLayout, QFileDialog, QGroupBox, 
                             QGraphicsView, QGraphicsScene, QGraphicsPathItem, QGraphicsRectItem, 
                             QGraphicsEllipseItem, QGraphicsTextItem, QSplitter)
from PyQt5.QtCore import Qt, QPointF, QRectF, QPoint, QTimer
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainterPath, QPainter, QCursor, QKeySequence

# ==========================================
# 1. NODE SYSTEM CORE
# ==========================================
class Edge(QGraphicsPathItem):
    def __init__(self, source_socket, dest_socket=None):
        super().__init__()
        self.source = source_socket
        self.dest = dest_socket
        self.setZValue(-1)
        self.setPen(QPen(QColor("#007acc"), 2, Qt.SolidLine))
        
    def update_position(self, mouse_pos=None):
        path = QPainterPath()
        start = self.source.scenePos()
        end = self.dest.scenePos() if self.dest else mouse_pos
        if not end: return
        path.moveTo(start)
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        path.cubicTo(QPointF(start.x(), start.y() + dy * 0.5), QPointF(end.x(), end.y() - dy * 0.5), end)
        self.setPath(path)

class Socket(QGraphicsEllipseItem):
    def __init__(self, parent, is_output=False):
        super().__init__(-5, -5, 10, 10, parent)
        self.is_output = is_output
        self.node = parent
        self.setBrush(QBrush(QColor("#ff9d00")))
        self.setPen(QPen(QColor("#000000"), 1))
        self.edges = []

class UINode(QGraphicsRectItem):
    def __init__(self, el_id, el_type, linked_el=None, is_root=False):
        super().__init__(0, 0, 140, 40)
        self.el_id = el_id
        self.el_type = el_type
        self.linked_el = linked_el
        self.is_root = is_root

        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges)
        
        self.setBrush(QBrush(QColor("#007acc" if is_root else "#333333")))
        self.setPen(QPen(QColor("#555555"), 2))
        
        lbl_text = f"[Window]\n{el_id}" if is_root else f"[{el_type}]\n{el_id}"
        self.label = QGraphicsTextItem(lbl_text, self)
        self.label.setDefaultTextColor(QColor("#ffffff" if is_root else "#dddddd"))
        self.label.setPos(5, 2)
        
        self.input_socket = Socket(self, is_output=False)
        self.input_socket.setPos(self.rect().width() / 2, 0)
        if is_root: self.input_socket.hide()
        
        self.output_socket = Socket(self, is_output=True)
        self.output_socket.setPos(self.rect().width() / 2, self.rect().height())

    def update_style(self, selected):
        color = "#ff9d00" if selected else ("#007acc" if self.is_root else "#555555")
        self.setPen(QPen(QColor(color), 2))

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionHasChanged:
            for edge in self.input_socket.edges + self.output_socket.edges: edge.update_position()
        elif change == QGraphicsRectItem.ItemSelectedHasChanged:
            if self.linked_el and hasattr(self.linked_el, 'main_window'):
                self.linked_el.main_window.sync_selection_from_node()
        return super().itemChange(change, value)


class NodeCanvasView(QGraphicsView):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag) 
        
        self.setStyleSheet("border: none; background-color: #1a1a1a;")
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        
        self.current_edge = None
        self.middle_mouse_pressed = False
        self.last_pan_pos = QPoint()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        left = int(rect.left()) - (int(rect.left()) % 20)
        top = int(rect.top()) - (int(rect.top()) % 20)
        lines = []
        for x in range(left, int(rect.right()), 20): lines.extend([QPointF(x, rect.top()), QPointF(x, rect.bottom())])
        for y in range(top, int(rect.bottom()), 20): lines.extend([QPointF(rect.left(), y), QPointF(rect.right(), y)])
        painter.setPen(QPen(QColor("#252525"), 1))
        painter.drawLines(lines)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self.setDragMode(QGraphicsView.NoDrag)
            return

        item = self.itemAt(event.pos())
        if isinstance(item, Socket) and item.is_output:
            self.setDragMode(QGraphicsView.NoDrag) 
            self.current_edge = Edge(item)
            self.scene.addItem(self.current_edge)
            return
                
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.middle_mouse_pressed:
            delta = event.pos() - self.last_pan_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_pan_pos = event.pos()
            return
        if self.current_edge:
            self.current_edge.update_position(self.mapToScene(event.pos()))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setDragMode(QGraphicsView.RubberBandDrag) 
        
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = False
            self.setCursor(Qt.ArrowCursor)
            return

        if self.current_edge:
            item = self.itemAt(event.pos())
            if isinstance(item, Socket) and not item.is_output and item.node != self.current_edge.source.node:
                child_node = item.node
                parent_node = self.current_edge.source.node
                
                if child_node.linked_el:
                    child_node.linked_el.el_parent_id = parent_node.el_id
                    self.main_window.populate_props_panel()
                    self.main_window.rebuild_node_wires() 
                    self.main_window.save_state() 
            
            self.scene.removeItem(self.current_edge)
            self.current_edge = None
            return

        super().mouseReleaseEvent(event)
        if self.scene.selectedItems():
            self.main_window.save_state()

    def wheelEvent(self, event):
        zoom = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom, zoom)


# ==========================================
# 2. VISUAL UI CANVAS ELEMENT
# ==========================================
class DraggableElement(QFrame):
    def __init__(self, parent, el_type, el_id, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.el_type = el_type
        self.el_id = el_id
        
        self.el_text = el_type
        self.el_event = "onClick" if el_type == "button" else "onChange"
        self.el_code = ""
        self.el_options = "Item 1, Item 2"
        self.el_min, self.el_max, self.el_value = 0, 100, 50
        self.el_parent_id = "win" 
        
        self.node = None 
        
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)
        self.setMouseTracking(True)
        self.is_resizing = False
        self.resize_margin = 15
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.mock_widget = None
        
        def_sizes = {
            "group": (200, 100), "panel": (200, 150), "tabbedpanel": (250, 150), "tab": (230, 120),
            "button": (120, 30), "checkbox": (150, 25), "radiobutton": (150, 25), 
            "slider": (180, 25), "progressbar": (180, 20), "statictext": (150, 25), 
            "edittext": (180, 30), "image": (100, 100), "dropdownlist": (150, 25), 
            "listbox": (150, 100), "treeview": (180, 120), "divider": (280, 10), "spacer": (280, 20)
        }
        w, h = def_sizes.get(el_type, (100, 30))
        self.resize(w, h)
        self.build_mock_widget()
        
    def build_mock_widget(self):
        if self.mock_widget: self.mock_widget.deleteLater()
        t = self.el_type
        self.mock_widget = QFrame()
        lay = QVBoxLayout(self.mock_widget)
        lay.setContentsMargins(2, 2, 2, 2)
        
        if t == "group":
            self.mock_widget.setStyleSheet("border: 1px dashed #666; background: rgba(255,255,255,0.05);")
            lbl = QLabel(f"[Group] {self.el_id}"); lbl.setStyleSheet("color:#777;"); lay.addWidget(lbl); lay.addStretch()
        elif t == "panel":
            self.mock_widget.setStyleSheet("border: 1px solid #777; background: #333;")
            lbl = QLabel(self.el_text); lbl.setStyleSheet("color:#aaa; border:none;"); lay.addWidget(lbl); lay.addStretch()
        elif t == "tabbedpanel":
            self.mock_widget.setStyleSheet("border: 1px solid #777; background: #333;")
            lbl = QLabel(f"TabbedPanel: {self.el_id}"); lbl.setStyleSheet("background:#444; padding:2px;"); lay.addWidget(lbl); lay.addStretch()
        elif t == "tab":
            self.mock_widget.setStyleSheet("border: 1px solid #555; background: #2b2b2b;")
            lay.addWidget(QLabel(f"Tab: {self.el_text}")); lay.addStretch()
        elif t == "button":
            btn = QPushButton(self.el_text); btn.setStyleSheet("background: #555; color: white;"); lay.addWidget(btn)
        elif t == "checkbox": lay.addWidget(QLabel(f"☑ {self.el_text}"))
        elif t == "radiobutton": lay.addWidget(QLabel(f"◉ {self.el_text}"))
        elif t == "slider":
            lbl = QLabel(f"{self.el_min} ──[█]── {self.el_max}"); lbl.setStyleSheet("background:#444; border:1px solid #222;"); lay.addWidget(lbl)
        elif t == "progressbar":
            lbl = QLabel(f"{self.el_value}%"); lbl.setStyleSheet("background: linear-gradient(to right, #007acc 50%, #444 50%); border:1px solid #222;")
            lbl.setAlignment(Qt.AlignCenter); lay.addWidget(lbl)
        elif t == "statictext": lbl = QLabel(self.el_text); lbl.setStyleSheet("color:#ddd;"); lay.addWidget(lbl)
        elif t == "edittext":
            inp = QTextEdit(self.el_text) if self.height() > 35 else QLineEdit(self.el_text)
            inp.setStyleSheet("background:#fff; color:#000;"); lay.addWidget(inp)
        elif t == "image":
            lbl = QLabel("[ IMAGE ]"); lbl.setStyleSheet("background:#222; border:1px solid #555; color:#777;"); lbl.setAlignment(Qt.AlignCenter); lay.addWidget(lbl)
        elif t == "dropdownlist":
            opts = [o.strip() for o in self.el_options.split(',') if o.strip()]
            cb = QComboBox(); cb.addItems(opts if opts else ["Select"])
            cb.setStyleSheet("background:#e0e0e0; color:#000;"); lay.addWidget(cb)
        elif t in ["listbox", "treeview"]:
            opts = [o.strip() for o in self.el_options.split(',') if o.strip()]
            txt = "\n".join(opts) if opts else "Item 1\nItem 2"
            lbl = QTextEdit(txt); lbl.setReadOnly(True); lbl.setStyleSheet("background:#fff; color:#000;"); lay.addWidget(lbl)
        elif t == "scrollbar":
            lbl = QLabel("↕"); lbl.setStyleSheet("background:#555;"); lbl.setAlignment(Qt.AlignCenter); lay.addWidget(lbl)
        elif t == "divider": self.mock_widget.setStyleSheet("border-top: 2px solid #555;")
        elif t == "spacer": self.mock_widget.setStyleSheet("border: 1px dashed #666; background: rgba(255,255,255,0.05);")
            
        if self.mock_widget:
            self.mock_widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            for child in self.mock_widget.findChildren(QWidget): child.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.layout.addWidget(self.mock_widget)
            
    def update_style(self, selected):
        self.setStyleSheet("QFrame { border: 2px dashed #ff9d00; background-color: rgba(255, 157, 0, 40); }" if selected else "QFrame { border: 1px solid transparent; background-color: transparent; }")

    def is_in_resize_zone(self, pos):
        return pos.x() >= self.width() - self.resize_margin and pos.y() >= self.height() - self.resize_margin

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            mods = QApplication.keyboardModifiers()
            if mods == Qt.ShiftModifier or mods == Qt.ControlModifier:
                self.main_window.toggle_selection(self)
            else:
                if self not in self.main_window.selected_elements:
                    self.main_window.set_selected_elements([self])
            
            if self.is_in_resize_zone(event.pos()):
                self.is_resizing = True
                self.start_global_pos = event.globalPos()
                self.start_size = self.size()
            else:
                self.is_resizing = False
                self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.is_in_resize_zone(event.pos()) and not event.buttons(): self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif not event.buttons(): self.setCursor(QCursor(Qt.SizeAllCursor))

        if event.buttons() == Qt.LeftButton:
            if self.is_resizing:
                dx = event.globalPos().x() - self.start_global_pos.x()
                dy = event.globalPos().y() - self.start_global_pos.y()
                self.resize(round(max(20, self.start_size.width() + dx) / 4) * 4, round(max(12, self.start_size.height() + dy) / 4) * 4)
                self.main_window.sync_props_from_canvas()
            else:
                new_pos = self.mapToParent(event.pos() - self.offset)
                x = max(0, min(round(new_pos.x() / 4) * 4, self.parent().width() - self.width()))
                y = max(0, min(round(new_pos.y() / 4) * 4, self.parent().height() - self.height()))
                
                dx_move = x - self.x()
                dy_move = y - self.y()
                
                # --- SMART PARENT DRAGGING (Moves children too) ---
                all_to_move = set(self.main_window.selected_elements)
                all_to_move.add(self)
                
                children_to_add = set()
                for el in all_to_move:
                    children_to_add.update(self.main_window.get_all_children(el.el_id))
                all_to_move.update(children_to_add)
                
                for el in all_to_move:
                    el.move(el.x() + dx_move, el.y() + dy_move)
                    
                self.main_window.sync_props_from_canvas()

    def mouseReleaseEvent(self, event): 
        self.is_resizing = False
        self.main_window.save_state()


# ==========================================
# 3. MAIN APPLICATION (THE AKASH KUMAR EDITION)
# ==========================================
class PhotoshopUIBuilder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1300, 900)
        
        self.elements = []
        self.selected_elements = [] 
        self.root_node = None
        self.id_counter = 0 
        self.syncing_selection = False
        self.clipboard = []
        
        self.current_save_path = None 
        self.is_dirty = False 
        
        self.undo_stack = []
        self.redo_stack = []
        self.is_undoing = False
        
        self.apply_dark_theme()
        self.init_ui()
        self.update_title()

    def update_title(self):
        title = "Photoshop UI Builder - Ultimate Pro Studio"
        if self.current_save_path:
            title += f" [{self.current_save_path}]"
        if self.is_dirty:
            title += " *"
        self.setWindowTitle(title)

    def closeEvent(self, event):
        if not self.prompt_save_if_dirty(): event.ignore()
        else: event.accept()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #2b2b2b; color: #dddddd; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
            QFrame[cssClass="panel"] { background-color: #323232; border: 1px solid #444; border-radius: 4px; }
            QPushButton { background-color: #4a4a4a; border: 1px solid #222; padding: 5px; border-radius: 3px; color: white; }
            QPushButton:hover { background-color: #555555; border: 1px solid #007acc; }
            QPushButton.primary { background-color: #007acc; font-weight: bold; }
            QPushButton.danger { background-color: #cc3333; }
            QPushButton.success { background-color: #27ae60; font-weight: bold; padding: 5px 15px;}
            QLineEdit, QTextEdit, QComboBox { background-color: #1e1e1e; border: 1px solid #555; padding: 4px; color: white; }
            QGroupBox { border: 1px solid #555; border-radius: 3px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; color: #aaa; }
            QSplitter::handle { background-color: #444; }
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_vlayout = QVBoxLayout(central_widget)
        main_vlayout.setContentsMargins(10, 10, 10, 5) # Reduce bottom margin for footer
        
        # TOP BAR
        top_bar = QFrame(); top_bar.setProperty("cssClass", "panel")
        top_bar_layout = QHBoxLayout(top_bar)
        
        btn_close = QPushButton("❌ Close"); btn_close.clicked.connect(self.close_project)
        btn_save = QPushButton("💾 Save"); btn_save.clicked.connect(lambda: self.save_file(save_as=False))
        btn_save_as = QPushButton("💾 Save As"); btn_save_as.clicked.connect(lambda: self.save_file(save_as=True))
        btn_load = QPushButton("📂 Load"); btn_load.clicked.connect(self.load_file)
        
        btn_cut = QPushButton("✂ Cut"); btn_cut.clicked.connect(self.cut_elements)
        btn_copy = QPushButton("📄 Copy"); btn_copy.clicked.connect(self.copy_elements)
        btn_paste = QPushButton("📋 Paste"); btn_paste.clicked.connect(self.paste_elements)
        btn_dup = QPushButton("🔁 Dup"); btn_dup.clicked.connect(self.duplicate_elements)
        
        btn_undo = QPushButton("↶ Undo"); btn_undo.clicked.connect(self.undo_action)
        btn_redo = QPushButton("↷ Redo"); btn_redo.clicked.connect(self.redo_action)
        btn_export = QPushButton("🚀 Export JSX"); btn_export.setProperty("class", "success"); btn_export.clicked.connect(self.export_jsx)
        
        btn_shortcuts = QPushButton("⌨ Shortcuts"); btn_shortcuts.setStyleSheet("background-color: #8e44ad; font-weight: bold;")
        btn_shortcuts.clicked.connect(self.show_shortcuts)

        top_bar_layout.addWidget(btn_close)
        top_bar_layout.addWidget(QLabel(" | "))
        for btn in [btn_save, btn_save_as, btn_load]: top_bar_layout.addWidget(btn)
        top_bar_layout.addStretch()
        for btn in [btn_cut, btn_copy, btn_paste, btn_dup]: top_bar_layout.addWidget(btn)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(btn_undo); top_bar_layout.addWidget(btn_redo)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(btn_shortcuts)
        top_bar_layout.addWidget(btn_export)
        main_vlayout.addWidget(top_bar)

        cols_layout = QHBoxLayout()

        # LEFT PANEL
        left_panel = QFrame(); left_panel.setProperty("cssClass", "panel"); left_panel.setFixedWidth(240)
        left_layout = QVBoxLayout(left_panel); left_layout.addWidget(QLabel("<b>ADD ELEMENTS</b>"))

        scroll_left = QScrollArea(); scroll_left.setWidgetResizable(True); scroll_left.setStyleSheet("border:none;")
        left_content = QWidget(); left_content_lay = QVBoxLayout(left_content)
        
        categories = {
            "Containers (Parents)": ["group", "panel", "tabbedpanel", "tab"],
            "Controls": ["button", "checkbox", "radiobutton", "slider", "progressbar"],
            "Text & Media": ["statictext", "edittext", "image"],
            "Lists & Selection": ["dropdownlist", "listbox", "treeview", "scrollbar"],
            "Layout Helpers": ["divider", "spacer"]
        }
        
        for cat, items in categories.items():
            grp = QGroupBox(cat); glay = QVBoxLayout(grp)
            for item in items:
                btn = QPushButton(f"+ {item}"); btn.clicked.connect(lambda checked, el=item: self.add_element(el))
                glay.addWidget(btn)
            left_content_lay.addWidget(grp)
            
        left_content_lay.addStretch(); scroll_left.setWidget(left_content)
        left_layout.addWidget(scroll_left); cols_layout.addWidget(left_panel)

        # CENTER PANEL (SPLITTER)
        splitter = QSplitter(Qt.Vertical)
        
        ui_wrapper = QWidget(); ui_layout = QVBoxLayout(ui_wrapper); ui_layout.setContentsMargins(0,0,0,0)
        setup_group = QWidget(); setup_layout = QHBoxLayout(setup_group)
        setup_layout.addWidget(QLabel("Title:")); self.inp_proj = QLineEdit("MyDialog"); setup_layout.addWidget(self.inp_proj)
        setup_layout.addWidget(QLabel("W:")); self.inp_w = QLineEdit("500"); self.inp_w.setFixedWidth(40); setup_layout.addWidget(self.inp_w)
        setup_layout.addWidget(QLabel("H:")); self.inp_h = QLineEdit("600"); self.inp_h.setFixedWidth(40); setup_layout.addWidget(self.inp_h)
        self.btn_init = QPushButton("Init Canvas"); self.btn_init.setProperty("class", "primary"); self.btn_init.clicked.connect(self.setup_canvas)
        setup_layout.addWidget(self.btn_init); ui_layout.addWidget(setup_group)

        scroll_center = QScrollArea(); scroll_center.setStyleSheet("border: none; background: #222;")
        self.canvas = QFrame(); self.canvas.setObjectName("canvas")
        self.canvas.setFixedSize(500, 600); self.canvas.setEnabled(False) 
        self.canvas.mousePressEvent = lambda e: self.set_selected_elements([]) 
        scroll_center.setWidget(self.canvas); scroll_center.setAlignment(Qt.AlignCenter)
        ui_layout.addWidget(scroll_center); splitter.addWidget(ui_wrapper)

        node_wrapper = QWidget(); node_layout = QVBoxLayout(node_wrapper); node_layout.setContentsMargins(0,0,0,0)
        self.canvas_view = NodeCanvasView(self); node_layout.addWidget(self.canvas_view)
        splitter.addWidget(node_wrapper); splitter.setSizes([400, 300])
        cols_layout.addWidget(splitter)

        # RIGHT PANEL (Properties & Alignment)
        right_panel = QFrame(); right_panel.setProperty("cssClass", "panel"); right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel); right_layout.addWidget(QLabel("<b>PROPERTIES</b>"))
        
        self.multi_select_widget = QWidget()
        ms_layout = QVBoxLayout(self.multi_select_widget); ms_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_multi = QLabel("Multiple Elements Selected.")
        lbl_multi.setStyleSheet("color: #007acc; font-weight: bold; margin-bottom: 5px;")
        ms_layout.addWidget(lbl_multi)
        
        align_grid = QGridLayout(); align_grid.setSpacing(5)
        btn_al = QPushButton("⇤ L"); btn_al.clicked.connect(lambda: self.align_elements('left'))
        btn_ac = QPushButton(">< C"); btn_ac.clicked.connect(lambda: self.align_elements('center_h'))
        btn_ar = QPushButton("⇥ R"); btn_ar.clicked.connect(lambda: self.align_elements('right'))
        btn_at = QPushButton("⇡ T"); btn_at.clicked.connect(lambda: self.align_elements('top'))
        btn_am = QPushButton("- M"); btn_am.clicked.connect(lambda: self.align_elements('center_v'))
        btn_ab = QPushButton("⇣ B"); btn_ab.clicked.connect(lambda: self.align_elements('bottom'))
        btn_dh = QPushButton("↔ Dist H"); btn_dh.clicked.connect(lambda: self.distribute_elements('h'))
        btn_dv = QPushButton("↕ Dist V"); btn_dv.clicked.connect(lambda: self.distribute_elements('v'))
        
        align_grid.addWidget(QLabel("Align H:"), 0, 0); align_grid.addWidget(btn_al, 0, 1); align_grid.addWidget(btn_ac, 0, 2); align_grid.addWidget(btn_ar, 0, 3)
        align_grid.addWidget(QLabel("Align V:"), 1, 0); align_grid.addWidget(btn_at, 1, 1); align_grid.addWidget(btn_am, 1, 2); align_grid.addWidget(btn_ab, 1, 3)
        align_grid.addWidget(QLabel("Space:"), 2, 0); align_grid.addWidget(btn_dh, 2, 1, 1, 1); align_grid.addWidget(btn_dv, 2, 2, 1, 2)
        ms_layout.addLayout(align_grid)
        ms_layout.addStretch()
        
        right_layout.addWidget(self.multi_select_widget); self.multi_select_widget.setVisible(False)
        
        self.prop_widget = QWidget(); p_layout = QVBoxLayout(self.prop_widget); p_layout.setContentsMargins(0, 0, 0, 0)
        self.p_id = self.add_prop_row(p_layout, "ID:")
        
        parent_row = QHBoxLayout(); lbl_parent = QLabel("Parent:"); lbl_parent.setFixedWidth(80)
        self.p_parent = QComboBox(); self.p_parent.currentIndexChanged.connect(self.manual_parent_change)
        parent_row.addWidget(lbl_parent); parent_row.addWidget(self.p_parent); p_layout.addLayout(parent_row)
        
        self.p_text = self.add_prop_row(p_layout, "Text:")
        
        grid = QGridLayout()
        grid.addWidget(QLabel("X:"), 0, 0); self.p_x = QLineEdit(); grid.addWidget(self.p_x, 0, 1)
        grid.addWidget(QLabel("Y:"), 0, 2); self.p_y = QLineEdit(); grid.addWidget(self.p_y, 0, 3)
        grid.addWidget(QLabel("W:"), 1, 0); self.p_w = QLineEdit(); grid.addWidget(self.p_w, 1, 1)
        grid.addWidget(QLabel("H:"), 1, 2); self.p_h = QLineEdit(); grid.addWidget(self.p_h, 1, 3)
        p_layout.addLayout(grid)
        
        layer_layout = QHBoxLayout()
        self.btn_layer_up = QPushButton("↑ Layer Up"); self.btn_layer_up.clicked.connect(self.layer_up)
        self.btn_layer_down = QPushButton("↓ Layer Down"); self.btn_layer_down.clicked.connect(self.layer_down)
        layer_layout.addWidget(self.btn_layer_up); layer_layout.addWidget(self.btn_layer_down)
        p_layout.addWidget(QLabel("Z-Index:")); p_layout.addLayout(layer_layout)

        p_layout.addWidget(QLabel("Options (,):")); self.p_options = QTextEdit(); self.p_options.setFixedHeight(40); p_layout.addWidget(self.p_options)
        
        slider_grid = QGridLayout()
        slider_grid.addWidget(QLabel("Val:"), 0, 0); self.p_val = QLineEdit(); slider_grid.addWidget(self.p_val, 0, 1)
        slider_grid.addWidget(QLabel("Min:"), 0, 2); self.p_min = QLineEdit(); slider_grid.addWidget(self.p_min, 0, 3)
        slider_grid.addWidget(QLabel("Max:"), 0, 4); self.p_max = QLineEdit(); slider_grid.addWidget(self.p_max, 0, 5)
        self.slider_widget = QWidget(); self.slider_widget.setLayout(slider_grid); p_layout.addWidget(self.slider_widget)
        
        p_layout.addWidget(QLabel("JS Action:")); self.p_event = QComboBox(); self.p_event.addItems(["None", "onClick", "onChange"]); p_layout.addWidget(self.p_event)
        self.p_code = QTextEdit(); self.p_code.setFixedHeight(60); p_layout.addWidget(self.p_code)
        
        btn_apply = QPushButton("Apply Properties"); btn_apply.setProperty("class", "primary"); btn_apply.clicked.connect(self.apply_properties)
        p_layout.addWidget(btn_apply)
        
        btn_del = QPushButton("Delete Selected"); btn_del.setProperty("class", "danger"); btn_del.clicked.connect(self.delete_element)
        p_layout.addWidget(btn_del)
        
        right_layout.addWidget(self.prop_widget); right_layout.addStretch()
        self.prop_widget.setVisible(False)
        cols_layout.addWidget(right_panel)

        main_vlayout.addLayout(cols_layout)

        # FOOTER (AUTHOR SIGNATURE)
        footer = QLabel("Developed by <b>Akash Kumar</b> | ✉ earthlyakash@gmail.com | License: Free | Version 14.1")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #777; padding: 5px;")
        main_vlayout.addWidget(footer)

    def add_prop_row(self, layout, label):
        row = QHBoxLayout(); lbl = QLabel(label); lbl.setFixedWidth(80); inp = QLineEdit()
        row.addWidget(lbl); row.addWidget(inp); layout.addLayout(row)
        return inp

    def show_shortcuts(self):
        text = """
        <h3 style='color:#007acc;'>Photoshop UI Builder Shortcuts</h3>
        <table border='0' cellspacing='5'>
        <tr><td><b>Ctrl + S</b></td><td>: Quick Save</td></tr>
        <tr><td><b>Ctrl + Shift + S</b></td><td>: Save As...</td></tr>
        <tr><td><b>Ctrl + C</b></td><td>: Copy</td></tr>
        <tr><td><b>Ctrl + X</b></td><td>: Cut</td></tr>
        <tr><td><b>Ctrl + V</b></td><td>: Paste</td></tr>
        <tr><td><b>Ctrl + D</b></td><td>: Duplicate</td></tr>
        <tr><td><b>Ctrl + Z</b></td><td>: Undo</td></tr>
        <tr><td><b>Ctrl + Y</b></td><td>: Redo (or Ctrl+Shift+Z)</td></tr>
        <tr><td><b>Delete</b></td><td>: Remove Selected</td></tr>
        <tr><td><b>Shift + Click</b></td><td>: Multi-select Elements</td></tr>
        </table>
        <br><p><i>Developed by Akash Kumar</i></p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setTextFormat(Qt.RichText)
        msg.setText(text)
        msg.exec_()

    # --- GET CHILDREN RECURSIVELY ---
    def get_all_children(self, el_id, children_set=None):
        if children_set is None: children_set = set()
        for el in self.elements:
            if el.el_parent_id == el_id and el not in children_set:
                children_set.add(el)
                self.get_all_children(el.el_id, children_set)
        return children_set

    # --- ALIGNMENT & DISTRIBUTION LOGIC ---
    def align_elements(self, mode):
        if len(self.selected_elements) < 2: return
        min_x = min([el.x() for el in self.selected_elements])
        min_y = min([el.y() for el in self.selected_elements])
        max_xw = max([el.x() + el.width() for el in self.selected_elements])
        max_yh = max([el.y() + el.height() for el in self.selected_elements])

        for el in self.selected_elements:
            if mode == 'left': el.move(min_x, el.y())
            elif mode == 'right': el.move(max_xw - el.width(), el.y())
            elif mode == 'top': el.move(el.x(), min_y)
            elif mode == 'bottom': el.move(el.x(), max_yh - el.height())
            elif mode == 'center_h': el.move(int((min_x + max_xw) / 2 - el.width() / 2), el.y())
            elif mode == 'center_v': el.move(el.x(), int((min_y + max_yh) / 2 - el.height() / 2))

        self.rebuild_node_wires()
        self.save_state()

    def distribute_elements(self, mode):
        if len(self.selected_elements) < 3: 
            QMessageBox.information(self, "Distribute", "Distribute karne ke liye kam se kam 3 elements select karein.")
            return

        if mode == 'h':
            sorted_els = sorted(self.selected_elements, key=lambda e: e.x())
            min_x, max_xw = sorted_els[0].x(), sorted_els[-1].x() + sorted_els[-1].width()
            total_w = sum([e.width() for e in sorted_els])
            gap = (max_xw - min_x - total_w) / (len(sorted_els) - 1)
            curr_x = min_x
            for el in sorted_els:
                el.move(int(curr_x), el.y()); curr_x += el.width() + gap
        elif mode == 'v':
            sorted_els = sorted(self.selected_elements, key=lambda e: e.y())
            min_y, max_yh = sorted_els[0].y(), sorted_els[-1].y() + sorted_els[-1].height()
            total_h = sum([e.height() for e in sorted_els])
            gap = (max_yh - min_y - total_h) / (len(sorted_els) - 1)
            curr_y = min_y
            for el in sorted_els:
                el.move(el.x(), int(curr_y)); curr_y += el.height() + gap

        self.rebuild_node_wires()
        self.save_state()

    # --- KEYBOARD SHORTCUTS ---
    def keyPressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
            if event.key() == Qt.Key_Z: self.redo_action()
            elif event.key() == Qt.Key_S: self.save_file(save_as=True)
        elif modifiers == Qt.ControlModifier:
            if event.key() == Qt.Key_Z: self.undo_action()
            elif event.key() == Qt.Key_Y: self.redo_action()
            elif event.key() == Qt.Key_X: self.cut_elements()
            elif event.key() == Qt.Key_C: self.copy_elements()
            elif event.key() == Qt.Key_V: self.paste_elements()
            elif event.key() == Qt.Key_D: self.duplicate_elements()
            elif event.key() == Qt.Key_S: self.save_file(save_as=False)
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_element()
        super().keyPressEvent(event)

    # --- UNDO / REDO ---
    def save_state(self):
        if self.is_undoing: return
        state = self.get_project_data()
        if self.undo_stack and self.undo_stack[-1] == state: return
        self.undo_stack.append(state)
        if len(self.undo_stack) > 30: self.undo_stack.pop(0) 
        self.redo_stack.clear()
        
        self.is_dirty = True
        self.update_title()

    def undo_action(self):
        if len(self.undo_stack) > 1:
            self.is_undoing = True
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            previous_state = self.undo_stack[-1]
            self.load_project_data(previous_state)
            self.is_undoing = False
            self.is_dirty = True
            self.update_title()

    def redo_action(self):
        if self.redo_stack:
            self.is_undoing = True
            next_state = self.redo_stack.pop()
            self.undo_stack.append(next_state)
            self.load_project_data(next_state)
            self.is_undoing = False
            self.is_dirty = True
            self.update_title()

    # --- COPY / CUT / PASTE SYSTEM ---
    def copy_elements(self):
        if not self.selected_elements: return
        self.clipboard = []
        for el in self.selected_elements:
            self.clipboard.append({
                "type": el.el_type, "id": el.el_id, "parent_id": el.el_parent_id,
                "text": el.el_text, "x": el.x(), "y": el.y(), "w": el.width(), "h": el.height(),
                "node_x": el.node.x(), "node_y": el.node.y(),
                "event": el.el_event, "code": el.el_code, "options": el.el_options,
                "val": el.el_value, "min": el.el_min, "max": el.el_max
            })

    def cut_elements(self):
        self.copy_elements()
        self.delete_element()

    def paste_elements(self):
        if not self.clipboard: return
        new_selection = []
        id_map = {} 
        
        for data in self.clipboard:
            new_el = self.add_element(data["type"], select=False, save_state=False)
            if not new_el: continue
            
            id_map[data["id"]] = new_el.el_id
            new_el.el_text = data["text"]; new_el.el_event = data["event"]
            new_el.el_code = data["code"]; new_el.el_options = data["options"]
            new_el.el_value, new_el.el_min, new_el.el_max = data["val"], data["min"], data["max"]
            new_el.setGeometry(data["x"] + 20, data["y"] + 20, data["w"], data["h"])
            new_el.build_mock_widget()
            new_el.node.setPos(data["node_x"] + 30, data["node_y"] + 30)
            new_selection.append((new_el, data["parent_id"]))
            
        for el, old_parent_id in new_selection:
            el.el_parent_id = id_map[old_parent_id] if old_parent_id in id_map else old_parent_id 
            final_selection = [e[0] for e in new_selection]
            
        self.rebuild_node_wires()
        self.set_selected_elements(final_selection)
        self.save_state()

    def duplicate_elements(self):
        if self.selected_elements:
            self.copy_elements()
            self.paste_elements()

    # --- PROJECT MANAGEMENT (CLOSE, SAVE, LOAD) ---
    def prompt_save_if_dirty(self):
        if not self.is_dirty: return True
        reply = QMessageBox.question(self, 'Unsaved Changes', 
                                     "Project mein unsaved changes hain. Kya aap save karna chahte hain?",
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if reply == QMessageBox.Save:
            self.save_file(save_as=False)
            return not self.is_dirty 
        elif reply == QMessageBox.Cancel:
            return False
        return True 

    def close_project(self):
        if self.prompt_save_if_dirty():
            self.canvas_view.scene.clear()
            for el in self.elements: el.deleteLater()
            self.elements.clear()
            self.set_selected_elements([])
            self.root_node = None
            self.undo_stack.clear()
            self.redo_stack.clear()
            
            self.current_save_path = None
            self.is_dirty = False
            self.update_title()
            
            self.canvas.setEnabled(False)
            self.canvas.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444;")
            self.inp_proj.setText("MyDialog")

    # --- THE FIX: UPDATE CANVAS WITHOUT CLEARING PROJECT ---
    def setup_canvas(self):
        try:
            w, h = int(self.inp_w.text()), int(self.inp_h.text())
            
            if not self.root_node:
                # Sirf tabhi project initialize karein jab root node na ho
                self.canvas.setFixedSize(w, h)
                self.canvas.setEnabled(True)
                self.btn_init.setText("Update Canvas")
                self.canvas.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444; background-image: radial-gradient(#333 1px, transparent 1px); background-size: 8px 8px;")
                
                self.root_node = UINode("win", "WindowRoot", is_root=True)
                self.canvas_view.scene.addItem(self.root_node)
                self.root_node.setPos(0, -100)
                self.root_node.ui_w = w
                self.root_node.ui_h = h
                self.save_state()
            else:
                # Agar root node already hai, toh sirf size badhayein, data na udayein!
                self.canvas.setFixedSize(w, h)
                self.root_node.ui_w = w
                self.root_node.ui_h = h
                self.save_state()
                
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid dimensions.")

    def add_element(self, el_type, select=True, save_state=True):
        if not self.canvas.isEnabled(): return None
        self.id_counter += 1
        el_id = f"{el_type.replace(' ', '_').lower()}_{self.id_counter}"
        
        el = DraggableElement(self.canvas, el_type, el_id, self)
        offset = (len(self.elements) % 10) * 10
        el.move(20 + offset, 20 + offset)
        el.show()
        
        node = UINode(el_id, el_type, linked_el=el)
        el.node = node
        self.canvas_view.scene.addItem(node)
        node.setPos(el.x(), el.y()) 
        
        self.elements.append(el)
        self.rebuild_node_wires() 
        
        if select: self.set_selected_elements([el])
        if save_state: self.save_state()
        return el

    def rebuild_node_wires(self):
        for item in self.canvas_view.scene.items():
            if isinstance(item, Edge): self.canvas_view.scene.removeItem(item)
                
        if self.root_node: self.root_node.output_socket.edges.clear()
        for el in self.elements:
            el.node.input_socket.edges.clear()
            el.node.output_socket.edges.clear()

        for child in self.elements:
            pid = child.el_parent_id
            parent = self.get_element_by_id(pid)
            if parent:
                p_node = parent if pid == "win" else parent.node
                edge = Edge(p_node.output_socket, child.node.input_socket)
                p_node.output_socket.edges.append(edge)
                child.node.input_socket.edges.append(edge)
                self.canvas_view.scene.addItem(edge)
                edge.update_position()

    def get_element_by_id(self, eid):
        if eid == "win": return self.root_node
        for el in self.elements:
            if el.el_id == eid: return el
        return None

    # --- SELECTION MANAGEMENT ---
    def toggle_selection(self, el):
        if el in self.selected_elements:
            self.selected_elements.remove(el)
            el.update_style(False)
            if el.node: el.node.setSelected(False)
        else:
            self.selected_elements.append(el)
            el.update_style(True)
            if el.node: el.node.setSelected(True)
        self.update_props_panel_visibility()

    def set_selected_elements(self, el_list):
        if self.syncing_selection: return
        self.syncing_selection = True
        
        for el in self.elements:
            is_sel = el in el_list
            el.update_style(is_sel)
            if el.node: el.node.setSelected(is_sel)
            
        self.selected_elements = el_list.copy()
        self.update_props_panel_visibility()
        self.syncing_selection = False

    def sync_selection_from_node(self):
        if self.syncing_selection: return
        selected_nodes = [item for item in self.canvas_view.scene.selectedItems() if isinstance(item, UINode) and not item.is_root]
        linked_els = [n.linked_el for n in selected_nodes if n.linked_el]
        self.set_selected_elements(linked_els)

    def update_props_panel_visibility(self):
        if len(self.selected_elements) == 0:
            self.prop_widget.setVisible(False)
            self.multi_select_widget.setVisible(False)
        elif len(self.selected_elements) == 1:
            self.prop_widget.setVisible(True)
            self.multi_select_widget.setVisible(False)
            self.populate_props_panel()
        else:
            self.prop_widget.setVisible(False)
            self.multi_select_widget.setVisible(True)

    def refresh_parent_dropdown(self):
        self.p_parent.blockSignals(True)
        self.p_parent.clear()
        self.p_parent.addItem("win (Main Window)", "win")
        containers = ["group", "panel", "tabbedpanel", "tab"]
        primary = self.selected_elements[0] if self.selected_elements else None
        for el in self.elements:
            if el.el_type in containers and el != primary:
                self.p_parent.addItem(f"{el.el_id} ({el.el_type})", el.el_id)
        self.p_parent.blockSignals(False)

    def manual_parent_change(self):
        if len(self.selected_elements) == 1:
            self.selected_elements[0].el_parent_id = self.p_parent.currentData()
            self.rebuild_node_wires()
            self.save_state()

    def populate_props_panel(self):
        if len(self.selected_elements) != 1: return
        el = self.selected_elements[0]
        self.p_id.setText(el.el_id)
        
        self.refresh_parent_dropdown()
        idx = self.p_parent.findData(el.el_parent_id)
        if idx >= 0:
            self.p_parent.blockSignals(True)
            self.p_parent.setCurrentIndex(idx)
            self.p_parent.blockSignals(False)
            
        self.p_text.setText(el.el_text)
        self.p_x.setText(str(el.x())); self.p_y.setText(str(el.y()))
        self.p_w.setText(str(el.width())); self.p_h.setText(str(el.height()))
        self.p_event.setCurrentText(el.el_event); self.p_code.setText(el.el_code)
        
        needs_opts = el.el_type in ["dropdownlist", "listbox", "treeview"]
        self.p_options.setVisible(needs_opts); self.p_options.setText(el.el_options)
        
        needs_slider = el.el_type in ["slider", "progressbar", "scrollbar"]
        self.slider_widget.setVisible(needs_slider)
        self.p_val.setText(str(el.el_value)); self.p_min.setText(str(el.el_min)); self.p_max.setText(str(el.el_max))

    def sync_props_from_canvas(self):
        if len(self.selected_elements) == 1:
            el = self.selected_elements[0]
            self.p_x.setText(str(el.x()))
            self.p_y.setText(str(el.y()))
            self.p_w.setText(str(el.width()))
            self.p_h.setText(str(el.height()))

    def apply_properties(self):
        if len(self.selected_elements) != 1: return
        el = self.selected_elements[0]
        try:
            el.el_id = self.p_id.text()
            el.el_text = self.p_text.text()
            el.el_event = self.p_event.currentText()
            el.el_code = self.p_code.toPlainText()
            el.el_options = self.p_options.toPlainText()
            if el.el_type in ["slider", "progressbar", "scrollbar"]:
                el.el_value, el.el_min, el.el_max = int(self.p_val.text()), int(self.p_min.text()), int(self.p_max.text())
            
            el.setGeometry(int(self.p_x.text()), int(self.p_y.text()), int(self.p_w.text()), int(self.p_h.text()))
            el.build_mock_widget()
            el.node.label.setPlainText(f"[{el.el_type}]\n{el.el_id}")
            self.save_state()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Check your number fields.")

    def delete_element(self):
        if not self.selected_elements: return
        for el in self.selected_elements:
            self.canvas_view.scene.removeItem(el.node)
            if el in self.elements: self.elements.remove(el)
            el.deleteLater()
        self.set_selected_elements([])
        self.rebuild_node_wires()
        self.save_state()

    def layer_up(self):
        if len(self.selected_elements) != 1: return
        el = self.selected_elements[0]
        idx = self.elements.index(el)
        if idx < len(self.elements) - 1:
            self.elements[idx], self.elements[idx+1] = self.elements[idx+1], self.elements[idx]
            for e in self.elements: e.raise_()
            self.save_state()

    def layer_down(self):
        if len(self.selected_elements) != 1: return
        el = self.selected_elements[0]
        idx = self.elements.index(el)
        if idx > 0:
            self.elements[idx], self.elements[idx-1] = self.elements[idx-1], self.elements[idx]
            for e in self.elements: e.raise_()
            self.save_state()

    # --- SAVE / LOAD DATA STRUCTURE ---
    def get_project_data(self):
        data = {
            "format": "DualViewUIBuilder", "title": self.inp_proj.text(),
            "width": int(self.inp_w.text()), "height": int(self.inp_h.text()), "elements": []
        }
        for el in self.elements:
            data["elements"].append({
                "type": el.el_type, "id": el.el_id, "parent_id": el.el_parent_id,
                "text": el.el_text, "x": el.x(), "y": el.y(), "w": el.width(), "h": el.height(),
                "event": el.el_event, "code": el.el_code, "options": el.el_options,
                "val": el.el_value, "min": el.el_min, "max": el.el_max,
                "node_x": el.node.pos().x(), "node_y": el.node.pos().y()
            })
        return data

    def load_project_data(self, data):
        self.inp_proj.setText(data.get("title", "MyDialog"))
        self.inp_w.setText(str(data.get("width", 500)))
        self.inp_h.setText(str(data.get("height", 600)))
        
        self.canvas.setFixedSize(int(self.inp_w.text()), int(self.inp_h.text()))
        self.canvas.setEnabled(True)
        self.canvas.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444; background-image: radial-gradient(#333 1px, transparent 1px); background-size: 8px 8px;")
        
        if not self.root_node:
            self.root_node = UINode("win", "WindowRoot", is_root=True)
            self.canvas_view.scene.addItem(self.root_node)
            self.root_node.setPos(0, -100)
            
        for el in self.elements:
            self.canvas_view.scene.removeItem(el.node)
            el.deleteLater()
        self.elements.clear()
        self.set_selected_elements([])
        
        max_id = 0
        for edata in data.get("elements", []):
            el = DraggableElement(self.canvas, edata["type"], edata["id"], self)
            el.el_parent_id = edata.get("parent_id", "win")
            el.el_text = edata.get("text", ""); el.el_event = edata.get("event", "None")
            el.el_code = edata.get("code", ""); el.el_options = edata.get("options", "")
            el.el_value, el.el_min, el.el_max = edata.get("val", 50), edata.get("min", 0), edata.get("max", 100)
            el.setGeometry(edata["x"], edata["y"], edata["w"], edata["h"])
            el.build_mock_widget(); el.show()
            
            node = UINode(edata["id"], edata["type"], linked_el=el)
            el.node = node; self.canvas_view.scene.addItem(node)
            node.setPos(edata["node_x"], edata["node_y"])
            
            self.elements.append(el)
            num_match = re.search(r'\d+$', edata["id"])
            if num_match: max_id = max(max_id, int(num_match.group()))
            
        self.id_counter = max_id
        self.rebuild_node_wires()
        for e in self.elements: e.raise_()

    def show_save_feedback(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QTimer.singleShot(300, QApplication.restoreOverrideCursor)

    def save_file(self, save_as=False):
        if not self.elements and not self.root_node:
            QMessageBox.warning(self, "Empty", "Save karne ke liye project mein elements hone chahiye.")
            return

        if save_as or not self.current_save_path:
            options = QFileDialog.Options()
            path, _ = QFileDialog.getSaveFileName(self, "Save UI Project", "ui_project.json", "JSON Files (*.json)", options=options)
            if not path: return
            self.current_save_path = path
            
        try:
            with open(self.current_save_path, 'w', encoding='utf-8') as f: 
                json.dump(self.get_project_data(), f, indent=4)
            
            self.is_dirty = False
            self.update_title()
            self.show_save_feedback() 
            
            if save_as:
                QMessageBox.information(self, "Saved", "Project saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def load_file(self):
        if not self.prompt_save_if_dirty(): return
        options = QFileDialog.Options()
        path, _ = QFileDialog.getOpenFileName(self, "Open UI Project", "", "JSON Files (*.json)", options=options)
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
            if data.get("format") != "DualViewUIBuilder":
                QMessageBox.warning(self, "Format Error", "Invalid file format.")
                return
                
            self.canvas_view.scene.clear()
            self.root_node = None 
            self.load_project_data(data)
            
            self.current_save_path = path
            self.is_dirty = False
            self.update_title()
            
            self.undo_stack.clear(); self.redo_stack.clear(); self.save_state() 
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project:\n{str(e)}")

    # --- JSX EXPORT ---
    def get_var_name(self, id_str):
        vname = re.sub(r'[^a-zA-Z0-9_]', '_', id_str)
        if not vname or (not vname[0].isalpha() and vname[0] != '_'): vname = f"var_{vname}"
        return vname

    def _export_children_recursive(self, parent_id, parent_var_name):
        jsx = ""
        children = [el for el in self.elements if el.el_parent_id == parent_id]
        
        for comp in children:
            parent_x, parent_y = 0, 0
            if parent_id != "win":
                parent = self.get_element_by_id(parent_id)
                if parent: parent_x, parent_y = parent.x(), parent.y()
            
            rel_x, rel_y = comp.x() - parent_x, comp.y() - parent_y
            t = comp.el_type
            bounds = "undefined" if t == "tab" else f"[{rel_x}, {rel_y}, {rel_x + comp.width()}, {rel_y + comp.height()}]"
            text = comp.el_text.replace("'", "\\'")
            opts_arr = str([o.strip() for o in comp.el_options.split(',') if o.strip()]).replace("'", '"')
            vname = self.get_var_name(comp.el_id)
            
            if t == "group": jsx += f"    var {vname} = {parent_var_name}.add('group', {bounds});\n"
            elif t == "panel": jsx += f"    var {vname} = {parent_var_name}.add('panel', {bounds}, '{text}');\n"
            elif t == "tabbedpanel": jsx += f"    var {vname} = {parent_var_name}.add('tabbedpanel', {bounds});\n"
            elif t == "tab": jsx += f"    var {vname} = {parent_var_name}.add('tab', {bounds}, '{text}');\n"
            elif t == "button": jsx += f"    var {vname} = {parent_var_name}.add('button', {bounds}, '{text}');\n"
            elif t == "checkbox": jsx += f"    var {vname} = {parent_var_name}.add('checkbox', {bounds}, '{text}');\n"
            elif t == "radiobutton": jsx += f"    var {vname} = {parent_var_name}.add('radiobutton', {bounds}, '{text}');\n"
            elif t == "slider": jsx += f"    var {vname} = {parent_var_name}.add('slider', {bounds}, {comp.el_value}, {comp.el_min}, {comp.el_max});\n"
            elif t == "progressbar": jsx += f"    var {vname} = {parent_var_name}.add('progressbar', {bounds}, {comp.el_min}, {comp.el_max});\n    {vname}.value = {comp.el_value};\n"
            elif t == "statictext": jsx += f"    var {vname} = {parent_var_name}.add('statictext', {bounds}, '{text}');\n"
            elif t == "edittext": jsx += f"    var {vname} = {parent_var_name}.add('edittext', {bounds}, '{text}'{', {multiline:true}' if comp.height() > 35 else ''});\n"
            elif t == "image": jsx += f"    var {vname} = {parent_var_name}.add('image', {bounds});\n"
            elif t == "dropdownlist": jsx += f"    var {vname} = {parent_var_name}.add('dropdownlist', {bounds}, {opts_arr});\n    {vname}.selection = 0;\n"
            elif t in ["listbox", "treeview"]: jsx += f"    var {vname} = {parent_var_name}.add('{t}', {bounds}, {opts_arr});\n"
            elif t == "scrollbar": jsx += f"    var {vname} = {parent_var_name}.add('scrollbar', {bounds}, {comp.el_value}, {comp.el_min}, {comp.el_max});\n"
            elif t == "divider": jsx += f"    var {vname} = {parent_var_name}.add('panel', {bounds});\n"
            elif t == "spacer": jsx += f"    var {vname} = {parent_var_name}.add('group', {bounds});\n"

            jsx += f"    controls['{comp.el_id}'] = {vname};\n"
            
            if comp.el_event != "None" and comp.el_code.strip():
                jsx += f"    {vname}.{comp.el_event} = function() {{\n"
                for line in comp.el_code.split('\n'): jsx += f"        {line}\n"
                jsx += f"    }};\n"
            jsx += "\n"
            jsx += self._export_children_recursive(comp.el_id, vname)
        return jsx

    def export_jsx(self):
        w, h = self.inp_w.text(), self.inp_h.text()
        title = self.inp_proj.text().replace("'", "\\'")
        jsx = f"#target photoshop\n// Generated from Studio Pro UI Builder (Akash Kumar Edition)\n\n(function () {{\n"
        jsx += f"    var win = new Window('dialog', '{title}');\n"
        jsx += f"    win.preferredSize = [{w}, {h}];\n    win.alignChildren = ['left', 'top'];\n    win.spacing = 0; win.margins = 0;\n\n    var controls = {{}};\n\n"
        jsx += self._export_children_recursive("win", "win")
        jsx += "    win.center();\n    win.show();\n})();\n"
        
        path, _ = QFileDialog.getSaveFileName(self, "Save JSX", "MyUI.jsx", "Photoshop Scripts (*.jsx)")
        if path:
            with open(path, 'w', encoding='utf-8') as f: f.write(jsx)
            QMessageBox.information(self, "Success", "JSX exported successfully!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PhotoshopUIBuilder()
    window.show()
    sys.exit(app.exec_())