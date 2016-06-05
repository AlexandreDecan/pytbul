from PyQt5 import QtGui, QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar

from functools import partial
from . import plotting
from .loader import load_from_xls

ABOUT_TITLE = 'Pytbul - visualisation de bulletins scolaires'
ABOUT_URL = 'https://github.com/AlexandreDecan/pytbul'
ABOUT_CONTENT = '\n'.join([
    ABOUT_TITLE + ' (Alexandre Decan, 2016)',
    '',
    'Cette application est distribuée sous les termes de la Licence Publique Générale GNU, v3.0.',
    'Une copie des termes de cette licence vous a été remise en même temps que cette application, et est également'
    'disponible en ligne à l\'adresse http://www.gnu.org/licenses/gpl-3.0.fr.html.',
    '',
    'Le code source de cette application est disponible à l\'adresse ' + ABOUT_URL + '.',
])


class GenericThread(QtCore.QThread):
    taskFinished = QtCore.pyqtSignal()

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.result = None

    def __del__(self):
        self.wait()

    def run(self):
        self.result = self._func(*self._args, **self._kwargs)
        self.taskFinished.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.df = None

        # Recent opened files
        self.recent_files = QtCore.QSettings().value('menu/recentFiles', None)
        self.recent_files = [] if self.recent_files is None else self.recent_files
        self.recent_files_maximum = 8

        # File menu
        fileMenu = self.menuBar().addMenu('&Fichier')

        self.menu_open = QtWidgets.QAction('&Ouvrir', fileMenu)
        self.menu_open.triggered.connect(self.choose_file)
        fileMenu.addAction(self.menu_open)

        # Submenu recent items
        submenu_recent = fileMenu.addMenu('&Récemment ouverts')
        self.menu_recent_items = []
        for i in range(self.recent_files_maximum):
            item = QtWidgets.QAction(submenu_recent)
            item.setVisible(False)
            item.triggered.connect(lambda : self.open_file(self.sender().data()))
            submenu_recent.addAction(item)

            self.menu_recent_items.append(item)

        submenu_recent.addSeparator()
        remove_recents = QtWidgets.QAction('&Vider la liste', submenu_recent)
        remove_recents.triggered.connect(self.clear_recent_files)
        submenu_recent.addAction(remove_recents)
        self.update_recent_files()

        self.menu_close = QtWidgets.QAction('&Fermer', fileMenu)
        self.menu_close.triggered.connect(partial(self.set_dataframe, None))
        fileMenu.addAction(self.menu_close)

        self.menu_quit = QtWidgets.QAction('&Quitter', fileMenu)
        self.menu_quit.triggered.connect(QtWidgets.qApp.quit)
        fileMenu.addAction(self.menu_quit)

        # About
        help_menu = self.menuBar().addMenu('&Aide')
        github = QtWidgets.QAction('Site web', help_menu)
        github.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(ABOUT_URL)))
        about = QtWidgets.QAction('&À propos', help_menu)
        about.triggered.connect(lambda: QtWidgets.QMessageBox.about(self, ABOUT_TITLE, ABOUT_CONTENT))
        help_menu.addAction(github)
        help_menu.addAction(about)

        self.update_ui()

    def open_file(self, filepath):
        # Remove from recent opened files
        try:
            self.recent_files.remove(filepath)
        except ValueError:
            pass

        try:
            f = open(filepath, 'r')
            f.close()
        except FileNotFoundError:
            QtWidgets.QMessageBox.critical(self, 'Ouverture d\'un fichier', 'Le fichier sélectionné n\'existe pas.')
            return
        except IOError:
            QtWidgets.QMessageBox.critical(self, 'Ouverture d\'un fichier', 'Le fichier sélectionné n\'est pas lisible.')
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Ouverture d\'un fichier', 'Impossible d\'ouvrir le fichier: %s' % str(e))
            return

        try:
            dataframe = load_from_xls(filepath)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Ouverture d\'un fichier', 'Impossible de lire le fichier: %s' % str(e))
            return

        self.set_dataframe(dataframe)

        # Add to recent opened files
        self.recent_files.insert(0, filepath)
        self.update_recent_files()

    def set_dataframe(self, dataframe):
        self.df = dataframe
        self.update_ui()

    def clear_recent_files(self):
        self.recent_files = []
        self.update_recent_files()

    def update_recent_files(self):
        self.recent_files = self.recent_files[:self.recent_files_maximum]

        for action in self.menu_recent_items:
            action.setVisible(False)

        for filepath, action in zip(self.recent_files, self.menu_recent_items):
            action.setText(QtCore.QFileInfo(filepath).fileName())
            action.setData(filepath)
            action.setVisible(True)

        # Update settings
        QtCore.QSettings().setValue('menu/recentFiles', self.recent_files)

    def update_ui(self):
        if self.df is None:
            frame = QtWidgets.QFrame()
            layout = QtWidgets.QVBoxLayout(frame)
            layout.addStretch(1)

            label = QtWidgets.QLabel('Choisissez un fichier pour commencer.', frame)
            layout.addWidget(label, 0, QtCore.Qt.AlignCenter)

            # button = QtWidgets.QPushButton('Ouvrir', self)
            # button.clicked.connect(self.menu_open.trigger)
            # layout.addWidget(button, 0, QtCore.Qt.AlignCenter)

            layout.addStretch(1)

            self.setCentralWidget(frame)
            self.menu_close.setEnabled(False)
        else:
            self.setCentralWidget(FrameDataFrame(self, self.df))
            self.menu_close.setEnabled(True)

    def choose_file(self):
        filepath, ok = QtWidgets.QFileDialog.getOpenFileName(filter='Feuille de calcul (*.xls *.ods);;Tous les fichiers (*.*)')

        if not ok:
            QtWidgets.QMessageBox.warning(self, 'Ouverture d\'un fichier', 'Veuillez choisir un fichier.')
            return
        else:
            self.open_file(filepath)


class DetachablePlotFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.figure = None
        self.canvas = None
        self.toolbar = None

        self.btn_detach = QtWidgets.QPushButton(self)
        self.btn_detach.setIcon(QtGui.QIcon.fromTheme('document-new-symbolic'))
        self.btn_detach.clicked.connect(self.detach_plot)

        self.btn_export = QtWidgets.QPushButton(self)
        self.btn_export.setIcon(QtGui.QIcon.fromTheme('document-save-symbolic'))
        self.btn_export.clicked.connect(self.save_plot)

        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setRowStretch(0, 1)
        self.layout.addWidget(self.btn_export, 1, 1, 1, 1)
        self.btn_export.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.layout.addWidget(self.btn_detach, 0, 1, 1, 1)
        self.btn_detach.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.resize(600, 400)

    def save_plot(self):
        filepath, ok = QtWidgets.QFileDialog.getSaveFileName(self, 'Enregistrer le graphique', filter='*.png')
        if ok:
            self.figure.savefig(filepath, bbox_inches='tight')

    def detach_plot(self):
        new_window = QtWidgets.QMainWindow(self)
        new_window.setWindowTitle('Graphique détaché')

        frame = QtWidgets.QFrame(new_window)

        canvas = FigureCanvas(self.figure)
        canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        canvas.updateGeometry()
        canvas.draw()

        toolbar = NavigationToolbar(canvas, frame)

        layout = QtWidgets.QVBoxLayout(frame)
        layout.addWidget(canvas, 1)
        layout.addWidget(toolbar, 0)

        new_window.setCentralWidget(frame)
        new_window.show()

        return new_window

    def update_figure(self, figure):
        self.figure = figure

        if self.canvas is not None:
            self.layout.removeWidget(self.canvas)
            self.layout.removeWidget(self.toolbar)
            self.canvas.deleteLater()

        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self.canvas.draw()

        self.layout.addWidget(self.canvas, 0, 0, 2, 1)


class FrameDataFrame(QtWidgets.QFrame):
    def __init__(self, parent, dataframe):
        super().__init__(parent)
        self.df = dataframe

        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.addTab(FrameSkills(self, self.df), 'Répartition des compétences')
        self.tabs.addTab(FrameEvolution(self, self.df), 'Évolution des tests')
        self.tabs.addTab(FrameGeneral(self, self.df), 'Vue générale')
        self.tabs.addTab(FrameStudents(self, self.df), 'Résultats individuels')
        self.tabs.setCurrentIndex(0)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.tabs, 1)
        self.tabs.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)


class FrameEvolution(QtWidgets.QFrame):
    def __init__(self, parent, dataframe):
        super().__init__(parent)
        self.df = dataframe

        self.plot = DetachablePlotFrame(self)
        self.skillsbox = QtWidgets.QGroupBox('Compétences', self)

        self.skills = QtWidgets.QButtonGroup(self.skillsbox)
        self.skills.buttonClicked.connect(self.update_figure)

        self.skills.addButton(QtWidgets.QRadioButton('Toutes les compétences', self.skillsbox))
        for skill in self.df['skill'].drop_duplicates().sort_values().values:
            self.skills.addButton(QtWidgets.QRadioButton(skill, self.skillsbox))
        self.skills.buttons()[0].setChecked(True)

        self.settings = QtWidgets.QGroupBox('Paramètres', self)
        self.quartiles = QtWidgets.QCheckBox('Quartiles', self.settings)
        self.quartiles.setChecked(True)
        self.quartiles.stateChanged.connect(self.update_figure)
        self.tests = QtWidgets.QCheckBox('Code des tests', self.settings)
        self.tests.setChecked(True)
        self.tests.stateChanged.connect(self.update_figure)

        # Layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.plot, 1)
        self.layout.addWidget(self.settings)
        settings_layout = QtWidgets.QVBoxLayout(self.settings)
        settings_layout.addWidget(self.quartiles)
        settings_layout.addWidget(self.tests)
        settings_layout.addStretch(1)

        self.layout.addWidget(self.skillsbox, 0)

        groupbox_layout = QtWidgets.QHBoxLayout(self.skillsbox)
        for radio in self.skills.buttons():
            groupbox_layout.addWidget(radio, 0)
        groupbox_layout.addStretch(1)

        self.update_figure()

    def update_figure(self):
        skill = self.skills.checkedButton().text()
        skill = None if skill == 'Toutes les compétences' else skill
        figure = plotting.tests_results_evolution(self.df, skill, display_tests=self.tests.isChecked(), display_quartiles=self.quartiles.isChecked())
        self.plot.update_figure(figure)


class FrameGeneral(QtWidgets.QFrame):
    def __init__(self, parent, dataframe):
        super().__init__(parent)
        self.df = dataframe

        self.plot = DetachablePlotFrame(self)
        self.settingbox = QtWidgets.QGroupBox('Paramètres', self)

        self.radiogroup = QtWidgets.QButtonGroup(self.settingbox)
        self.radiogroup.addButton(QtWidgets.QRadioButton('Grouper par étudiant', self.settingbox))
        self.radiogroup.addButton(QtWidgets.QRadioButton('Grouper par test', self.settingbox))
        self.radiogroup.buttons()[0].setChecked(True)
        self.radiogroup.buttonClicked.connect(self.update_figure)

        self.normalized = QtWidgets.QCheckBox('Normaliser', self.settingbox)
        self.normalized.stateChanged.connect(self.update_figure)

        self.skillsbox = QtWidgets.QGroupBox('Compétences', self)
        self.skills = QtWidgets.QButtonGroup(self.skillsbox)
        self.skills.buttonClicked.connect(self.update_figure)

        radio = QtWidgets.QRadioButton('Toutes les compétences', self.skillsbox)
        radio.setChecked(True)
        self.skills.addButton(radio)
        for skill in self.df['skill'].drop_duplicates().sort_values().values:
            self.skills.addButton(QtWidgets.QRadioButton(skill, self.skillsbox))

        # Layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.plot, 1)
        self.layout.addWidget(self.settingbox, 0)

        groupbox_layout = QtWidgets.QVBoxLayout(self.settingbox)
        radio_layout = QtWidgets.QHBoxLayout()
        for radio in self.radiogroup.buttons():
            radio_layout.addWidget(radio, 0)
        radio_layout.addStretch(1)
        groupbox_layout.addLayout(radio_layout)
        groupbox_layout.addWidget(self.normalized, 0)

        self.layout.addWidget(self.skillsbox, 0)

        groupbox_layout = QtWidgets.QHBoxLayout(self.skillsbox)
        for radio in self.skills.buttons():
            groupbox_layout.addWidget(radio, 0)
        groupbox_layout.addStretch(1)

        self.update_figure()

    def update_figure(self):
        normalized = self.normalized.isChecked()
        group_by = 'name' if self.radiogroup.checkedButton().text() == 'Grouper par étudiant' else 'code'

        skill = self.skills.checkedButton().text()
        skill = None if skill == 'Toutes les compétences' else skill
        figure = plotting.results_overview(self.df, normalized=normalized, group_by=group_by, skill=skill)
        self.plot.update_figure(figure)


class FrameSkills(QtWidgets.QFrame):
    def __init__(self, parent, dataframe):
        super().__init__(parent)
        self.df = dataframe

        self.plot = DetachablePlotFrame(self)
        self.settingbox = QtWidgets.QGroupBox('Paramètres', self)

        self.radiogroup = QtWidgets.QButtonGroup(self.settingbox)
        self.radiogroup.addButton(QtWidgets.QRadioButton('En nombre', self.settingbox))
        self.radiogroup.addButton(QtWidgets.QRadioButton('En poids', self.settingbox))
        self.radiogroup.buttons()[0].setChecked(True)
        self.radiogroup.buttonClicked.connect(self.update_figure)

        # Layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.plot, 1)
        self.layout.addWidget(self.settingbox, 0)

        groupbox_layout = QtWidgets.QVBoxLayout(self.settingbox)
        radio_layout = QtWidgets.QHBoxLayout()
        for radio in self.radiogroup.buttons():
            radio_layout.addWidget(radio, 0)
        radio_layout.addStretch(1)
        groupbox_layout.addLayout(radio_layout)

        self.update_figure()

    def update_figure(self):
        by_number = self.radiogroup.checkedButton().text() == 'En nombre'
        self.plot.update_figure(plotting.skills_distribution(self.df, by_number))


class FrameStudents(QtWidgets.QFrame):
    def __init__(self, parent, dataframe):
        super().__init__(parent)
        self.df = dataframe
        self.canvas = None

        self.plot = DetachablePlotFrame(self)
        self.studentsbox = QtWidgets.QGroupBox('Étudiants', self)
        self.settingsbox = QtWidgets.QGroupBox('Paramètres', self)
        self.skillsbox = QtWidgets.QGroupBox('Compétences', self)

        self.studentslist = QtWidgets.QComboBox(self.studentsbox)
        self.studentslist.addItems(self.df['name'].drop_duplicates().sort_values().values)
        self.studentslist.currentIndexChanged.connect(self.update_figure)

        self.normalize = QtWidgets.QCheckBox('Normaliser', self.settingsbox)
        self.normalize.stateChanged.connect(self.update_figure)
        self.regression = QtWidgets.QCheckBox('Régression', self.settingsbox)
        self.regression.setChecked(True)
        self.regression.stateChanged.connect(self.update_figure)
        self.tests = QtWidgets.QCheckBox('Code des tests', self.settingsbox)
        self.tests.setChecked(True)
        self.tests.stateChanged.connect(self.update_figure)

        self.skills = QtWidgets.QButtonGroup(self.skillsbox)
        self.skills.buttonClicked.connect(self.update_figure)

        radio = QtWidgets.QRadioButton('Toutes les compétences', self.skillsbox)
        radio.setChecked(True)
        self.skills.addButton(radio)
        for skill in self.df['skill'].drop_duplicates().sort_values().values:
            self.skills.addButton(QtWidgets.QRadioButton(skill, self.skillsbox))

        # Students layout
        student_layout = QtWidgets.QHBoxLayout(self.studentsbox)
        student_layout.addWidget(self.studentslist)

        # Settings layout
        settings_layout = QtWidgets.QVBoxLayout(self.settingsbox)
        settings_layout.addWidget(self.normalize)
        settings_layout.addWidget(self.regression)
        settings_layout.addWidget(self.tests)

        # Skills layout
        skills_layout = QtWidgets.QHBoxLayout(self.skillsbox)
        for radio in self.skills.buttons():
            skills_layout.addWidget(radio, 0)
        skills_layout.addStretch(1)

        # General layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.plot, 1)
        sublayout = QtWidgets.QHBoxLayout()
        sublayout.addWidget(self.studentsbox)
        sublayout.addWidget(self.settingsbox)
        self.layout.addLayout(sublayout)
        self.layout.addWidget(self.skillsbox)

        self.update_figure()

    def update_figure(self, *args):
        skill = self.skills.checkedButton().text()
        skill = None if skill == 'Toutes les compétences' else skill
        figure = plotting.student_results(self.df,
                                          student=self.studentslist.currentText(),
                                          normalized=self.normalize.checkState(),
                                          regression=self.regression.checkState(),
                                          display_tests=self.tests.checkState(),
                                          skill=skill)

        self.plot.update_figure(figure)


def main(argv):
    app = QtWidgets.QApplication(argv)
    app.setApplicationName('pytbul')
    app.setOrganizationName('decan')
    app.setOrganizationDomain('decan.lexpage.net')

    window = MainWindow()
    window.setWindowTitle('pytbul')
    window.resize(1000, 800)
    window.show()
    app.exec_()
