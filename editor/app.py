import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QInputDialog, QMenuBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from editor.controller import EditorController
from editor.views.world_form import WorldForm
from editor.views.location_form import LocationForm
from editor.views.place_form import PlaceForm
from editor.views.npc_form import NPCForm
from editor.views.player_form import PlayerForm

class StoryEditorApp(QMainWindow):
    """
    Ventana principal del editor de historias AAdventure.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Historias - AAdventure")
        self.resize(1000, 700)

        self.controller = EditorController()
        
        # 1. Configurar barra de menús
        self.setup_menu()

        # 2. Configurar el widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Usar un divisor para separar el árbol del formulario
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Panel Izquierdo: Árbol y Botones de Creación
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Estructura de la Aventura")
        self.tree.itemSelectionChanged.connect(self.on_tree_item_selected)
        left_layout.addWidget(self.tree)

        # Botones para crear entidades rápidamente
        btn_layout = QVBoxLayout()
        self.add_loc_btn = QPushButton("Añadir Localización...")
        self.add_loc_btn.clicked.connect(self.on_add_location)
        self.add_place_btn = QPushButton("Añadir Lugar a Localización...")
        self.add_place_btn.clicked.connect(self.on_add_place)
        self.add_npc_btn = QPushButton("Añadir NPC...")
        self.add_npc_btn.clicked.connect(self.on_add_npc)
        
        btn_layout.addWidget(self.add_loc_btn)
        btn_layout.addWidget(self.add_place_btn)
        btn_layout.addWidget(self.add_npc_btn)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_panel)

        # Panel Derecho: Formularios Dinámicos
        self.stacked_widget = QStackedWidget()
        
        # Inicializar todos los formularios
        self.world_form = WorldForm(self)
        self.location_form = LocationForm(self)
        self.place_form = PlaceForm(self.controller, self)
        self.npc_form = NPCForm(self)
        self.player_form = PlayerForm(self)
        
        # Conectar señales de cambio de nombre para actualizar el árbol en tiempo real
        self.world_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.location_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.place_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.npc_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)
        self.player_form.name_edit.textChanged.connect(self.update_selected_tree_item_text)

        # Pantalla de bienvenida / vacía
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        self.welcome_label = QLabel("Bienvenido al Editor de Historias de AAdventure\n\nCrea una nueva aventura o abre un archivo (.aad) para empezar.")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(self.welcome_label)

        # Añadir al stacked widget
        self.stacked_widget.addWidget(self.world_form)     # Index 0
        self.stacked_widget.addWidget(self.location_form)  # Index 1
        self.stacked_widget.addWidget(self.place_form)     # Index 2
        self.stacked_widget.addWidget(self.npc_form)       # Index 3
        self.stacked_widget.addWidget(self.player_form)    # Index 4
        self.stacked_widget.addWidget(self.welcome_widget) # Index 5
        
        self.stacked_widget.setCurrentIndex(5)
        splitter.addWidget(self.stacked_widget)

        # Ajustar ancho inicial del divisor (30% árbol, 70% formulario)
        splitter.setSizes([300, 700])

        # Cargar proyecto vacío por defecto al arrancar
        self.on_new_story()

    def setup_menu(self):
        menubar = self.menuBar()

        # Menú Archivo
        file_menu = menubar.addMenu("Archivo")

        new_action = QAction("Nueva Historia", self)
        new_action.triggered.connect(self.on_new_story)
        file_menu.addAction(new_action)

        open_action = QAction("Abrir Historia (.aad)...", self)
        open_action.triggered.connect(self.on_open_story)
        file_menu.addAction(open_action)

        save_action = QAction("Guardar", self)
        save_action.triggered.connect(self.on_save_story)
        file_menu.addAction(save_action)

        save_as_action = QAction("Guardar Como (.aad)...", self)
        save_as_action.triggered.connect(self.on_save_story_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def refresh_tree(self):
        self.tree.clear()
        if not self.controller.world:
            return

        # 1. Nodo de primer nivel: Mundo
        world_item = QTreeWidgetItem(self.tree)
        world_item.setText(0, f"Mundo: {self.controller.world.name}")
        world_item.setData(0, Qt.UserRole, ("world", self.controller.world))

        # Localizaciones y lugares directamente bajo Mundo
        for loc in self.controller.get_locations():
            loc_item = QTreeWidgetItem(world_item)
            loc_item.setText(0, f"Localización: {loc.name}")
            loc_item.setData(0, Qt.UserRole, ("location", loc))
            for place in loc.places:
                place_item = QTreeWidgetItem(loc_item)
                place_item.setText(0, f"Lugar: {place.name}")
                place_item.setData(0, Qt.UserRole, ("place", place))

        # 2. Nodo de primer nivel: NPCs
        npcs_group = QTreeWidgetItem(self.tree)
        npcs_group.setText(0, "Personajes (NPCs)")
        npcs_group.setData(0, Qt.UserRole, ("npcs_group", None))
        for npc in self.controller.get_npcs():
            npc_item = QTreeWidgetItem(npcs_group)
            npc_item.setText(0, f"NPC: {npc.name}")
            npc_item.setData(0, Qt.UserRole, ("npc", npc))

        # 3. Nodo de primer nivel: Jugador
        player_item = QTreeWidgetItem(self.tree)
        player_item.setText(0, f"Jugador: {self.controller.player.name if self.controller.player else 'Aventurero'}")
        player_item.setData(0, Qt.UserRole, ("player", self.controller.player))

        self.tree.expandAll()

    def update_selected_tree_item_text(self, text: str):
        """
        Actualiza el texto del elemento seleccionado en el árbol en tiempo real
        para reflejar los cambios en el campo de edición del formulario.
        """
        item = self.tree.currentItem()
        if not item:
            return
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        item_type, _ = data
        if item_type == "world":
            item.setText(0, f"Mundo: {text}")
        elif item_type == "location":
            item.setText(0, f"Localización: {text}")
        elif item_type == "place":
            item.setText(0, f"Lugar: {text}")
        elif item_type == "npc":
            item.setText(0, f"NPC: {text}")
        elif item_type == "player":
            item.setText(0, f"Jugador: {text}")

    def on_tree_item_selected(self):
        item = self.tree.currentItem()
        if not item:
            self.stacked_widget.setCurrentIndex(5)
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            self.stacked_widget.setCurrentIndex(5)
            return

        item_type, obj = data
        if item_type == "world":
            self.world_form.set_world(obj)
            self.stacked_widget.setCurrentWidget(self.world_form)
        elif item_type == "location":
            self.location_form.set_location(obj)
            self.stacked_widget.setCurrentWidget(self.location_form)
        elif item_type == "place":
            all_places = self.controller.get_all_places()
            all_npcs = self.controller.get_npcs()
            self.place_form.set_place(obj, all_places, all_npcs)
            self.stacked_widget.setCurrentWidget(self.place_form)
        elif item_type == "npc":
            self.npc_form.set_npc(obj)
            self.stacked_widget.setCurrentWidget(self.npc_form)
        elif item_type == "player":
            all_places = self.controller.get_all_places()
            self.player_form.set_player(obj, all_places)
            self.stacked_widget.setCurrentWidget(self.player_form)

    # --- ACCIONES DE ARCHIVO ---

    def on_new_story(self):
        self.controller.new_story()
        self.refresh_tree()
        self.stacked_widget.setCurrentIndex(5)
        self.statusBar().showMessage("Nueva historia creada.")

    def on_open_story(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Aventura", "", "Archivos AAdventure (*.aad)"
        )
        if file_path:
            try:
                self.controller.load_story(file_path)
                self.refresh_tree()
                self.stacked_widget.setCurrentIndex(5)
                self.statusBar().showMessage(f"Historia cargada: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Cargar", f"No se pudo cargar la aventura:\n{e}")

    def on_save_story(self):
        if self.controller.current_file_path:
            try:
                self.controller.save_story(self.controller.current_file_path)
                self.statusBar().showMessage(f"Historia guardada en {os.path.basename(self.controller.current_file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar la aventura:\n{e}")
        else:
            self.on_save_story_as()

    def on_save_story_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Aventura Como", "", "Archivos AAdventure (*.aad)"
        )
        if file_path:
            # Asegurar extensión
            if not file_path.lower().endswith(".aad"):
                file_path += ".aad"
            try:
                self.controller.save_story(file_path)
                self.statusBar().showMessage(f"Historia guardada como {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar la aventura:\n{e}")

    # --- ACCIONES DE CREACIÓN DE ENTIDADES ---

    def on_add_location(self):
        if not self.controller.world:
            return
        name, ok = QInputDialog.getText(self, "Añadir Localización", "Nombre de la localización:")
        if ok and name.strip():
            self.controller.add_location(name.strip(), "")
            self.refresh_tree()
            self.statusBar().showMessage(f"Localización '{name}' añadida.")

    def on_add_place(self):
        # Para añadir un lugar, el usuario debe tener seleccionada la localización a la que pertenece
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Añadir Lugar", "Por favor, selecciona una Localización en el árbol primero.")
            return

        data = item.data(0, Qt.UserRole)
        if not data or data[0] != "location":
            QMessageBox.warning(self, "Añadir Lugar", "Debes seleccionar un nodo de tipo Localización en el árbol para añadirle un lugar.")
            return

        location = data[1]
        name, ok = QInputDialog.getText(self, "Añadir Lugar", f"Nombre del lugar para {location.name}:")
        if ok and name.strip():
            self.controller.add_place(location.id, name.strip(), "")
            self.refresh_tree()
            self.statusBar().showMessage(f"Lugar '{name}' añadido a {location.name}.")

    def on_add_npc(self):
        if not self.controller.world:
            return
        name, ok = QInputDialog.getText(self, "Añadir NPC", "Nombre del personaje:")
        if ok and name.strip():
            self.controller.add_npc(name.strip(), "")
            self.refresh_tree()
            self.statusBar().showMessage(f"NPC '{name}' añadido.")
