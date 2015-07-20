
from PySide import QtGui
from PySide import QtCore
Qt = QtCore.Qt

from pytd.gui.itemviews.utils import ItemUserFlag
from pytd.util.qtutils import toColorSheet

from .ui.property_widget import Ui_PropertyWidget
from .ui.property_editor_view import Ui_PropertyEditorView

class PropertyWidget(QtGui.QWidget, Ui_PropertyWidget):

    def __init__(self, sProperty, parent=None):
        super(PropertyWidget, self).__init__(parent)
        self.setupUi(self)

        self.nameLabel.setObjectName(sProperty + "Label")
        self.nameLabel.setText(sProperty)

        self.dataLabel.setObjectName(sProperty + "Reader")

        self.propertyName = sProperty

class PropertyWidgetDelegate(QtGui.QStyledItemDelegate):

    def __init__(self, parent=None):
        super(PropertyWidgetDelegate, self).__init__(parent)

    def setEditorData(self, editor, index):

        if isinstance(editor, QtGui.QLabel):

            value = index.data(Qt.DisplayRole)
            editor.setText(value)

            if (index.flags() & Qt.ItemIsEditable):
                editor.setTextInteractionFlags(Qt.TextSelectableByKeyboard)

                qBrush = index.data(Qt.BackgroundRole)
                sBgColor = toColorSheet(qBrush.color()) if qBrush else "none"

                editor.setStyleSheet("QLabel {{ background-color: {0}; color: palette(text); }}".format(sBgColor))

            else:
                editor.setTextInteractionFlags(Qt.TextSelectableByMouse)
                editor.setStyleSheet("QLabel {color: gray;}")

        QtGui.QStyledItemDelegate.setEditorData(self, editor, index)

class PropertyWidgetMapper(QtGui.QDataWidgetMapper):

    def __init__(self, parent=None):
        super(PropertyWidgetMapper, self).__init__(parent)
        self.setSubmitPolicy(QtGui.QDataWidgetMapper.ManualSubmit)

    def indexFromWidget(self, widget):

        section = self.mappedSection(widget)
        if section == -1:
            return QtCore.QModelIndex()

        idx = self.currentIndex()

        if self.orientation() == Qt.Vertical:
            return self.model().index(section, idx, self.rootIndex())
        else:
            return self.model().index(idx, section, self.rootIndex())

class PropertyEditorView(QtGui.QWidget, Ui_PropertyEditorView):

    def __init__(self, parent=None):
        super(PropertyEditorView , self).__init__(parent)

        self.setupUi(self)

        self.mapper = PropertyWidgetMapper(self)
        self.setItemDelegate(PropertyWidgetDelegate(self))

        self.dataWidgetsDct = {"image": self.imageButton}
        self.categoryProperties = []

#        self.currentItem = None
        self.treeWidget = None

        self.__topMargin = self.propertyEditorLayout.contentsMargins().top()
        self.__bottomMargin = self.propertyEditorLayout.contentsMargins().bottom()

    def model(self):
        return self.mapper.model()

    def clearWidgetMapping(self):

        self.mapper.clearMapping()

        if not self.dataWidgetsDct:
            return

        for widget in self.dataWidgetsDct.itervalues():
            widget.clear()

    def buildWidgetMapping(self):

        self.clearWidgetMapping()

        model = self.model()
        mapper = self.mapper

        sPropertyList = model.propertyNames

        dataWidgetsDct = self.dataWidgetsDct

        for iSection, sProperty in enumerate(sPropertyList):

            if sProperty in dataWidgetsDct:
                widget = dataWidgetsDct[sProperty]
            else:
                readerWdg = PropertyWidget(sProperty, self.propertiesWidget)
                self.propertiesLayout.addWidget(readerWdg)

                readerWdg.nameLabel.setText(model.headerData(iSection, mapper.orientation()))

                widget = readerWdg.dataLabel
                dataWidgetsDct[sProperty] = widget

            mapper.addMapping(widget, iSection)

        self.propertiesLayout.insertStretch(-1)

        return dataWidgetsDct

    def updateReadersVisibility(self):

        mapper = self.mapper
        model = mapper.model()

        for sProperty, mappedWdg in self.dataWidgetsDct.iteritems():

            bVisible = False
            bEditable = False

            index = mapper.indexFromWidget(mappedWdg)
            prptyItem = model.itemFromIndex(index)
            if prptyItem and prptyItem.isValid():
                bVisible = (sProperty in self.categoryProperties)
                bEditable = prptyItem.flags() & Qt.ItemIsEditable

            reader = mappedWdg.parent()
            if isinstance(reader, PropertyWidget):
                reader.setVisible(bVisible)
                sColor = "color: palette(text)" if bEditable else "color: palette(gray)"
                reader.nameLabel.setStyleSheet(sColor)

    def itemDelegate(self):
        return self.mapper.itemDelegate()

    def setItemDelegate(self, newDelegate):

        oldDelegate = self.itemDelegate()

        if oldDelegate:

            try: oldDelegate.commitData.disconnect(self.commitData)
            except RuntimeError: pass

            try: oldDelegate.closeEditor.disconnect(self.closeEditor)
            except RuntimeError: pass

        if newDelegate:
            newDelegate.commitData.connect(self.commitData)
            newDelegate.closeEditor.connect(self.closeEditor)

        self.mapper.setItemDelegate(newDelegate)

    def disconnectFromTreeWidget(self):

        if not self.treeWidget:
            return

        treeWidget = self.treeWidget

        selModel = treeWidget.selectionModel()
        selModel.currentRowChanged.disconnect(self.setCurrentModelIndex)
        treeWidget.treeView.clicked.disconnect(self.setCurrentModelIndex)

        childrenView = treeWidget.childrenWidget.childrenView

        selModel = childrenView.selectionModel()
        selModel.currentRowChanged.disconnect(self.setCurrentModelIndex)


    def connectToTreeWidget(self, treeWidget):

        self.setModel(treeWidget.model())

        selModel = treeWidget.selectionModel()
        selModel.currentRowChanged.connect(self.setCurrentModelIndex)
        treeWidget.treeView.clicked.connect(self.setCurrentModelIndex)

        childrenView = treeWidget.childrenWidget.childrenView

        selModel = childrenView.selectionModel()
        selModel.currentRowChanged.connect(self.setCurrentModelIndex)

        self.treeWidget = treeWidget

    def setModel(self, model):

        if isinstance(model, QtGui.QSortFilterProxyModel):
            newModel = model.sourceModel()
        else:
            newModel = model

        self.mapper.setModel(newModel)

        self.buildWidgetMapping()

        self.setUiCategory("ZZ_Dev" if 0 else "XX_All")


    def setCurrentModelIndex(self, curntIndex):

        if not curntIndex.isValid():
            srcIndex = curntIndex
            model = self.model()
        else:
            model = curntIndex.model()

        if isinstance(model, QtGui.QSortFilterProxyModel):
            srcIndex = model.mapToSource(curntIndex)
            model = model.sourceModel()
        else:
            srcIndex = curntIndex

        self.mapper.setRootIndex(srcIndex.parent())
        self.mapper.setCurrentModelIndex(srcIndex)

        self.updateReadersVisibility()

    def setUiCategory(self, categoryKey):

        model = self.model()
        self.categoryProperties = model.getPrptiesFromUiCategory(categoryKey)
        self.updateReadersVisibility()


    def closeEditor(self, editor, hint):

        if isinstance(editor, QtGui.QLabel):
            return

        readerWidget = editor.parent()
        if isinstance(readerWidget, PropertyWidget):
            editedReader = readerWidget.dataLabel
        else:
            return

        self.mapper.removeMapping(editor)

        editor.setAttribute(Qt.WA_DeleteOnClose, True)
        editor.close()

        editedReader.setVisible(True)

    def commitData(self, editor):

        if isinstance(editor, QtGui.QLabel):
            return

        editedIndex = self.mapper.indexFromWidget(editor)
        if not editedIndex.isValid():
            return

        editedModel = editedIndex.model()

        delegate = self.itemDelegate()

        editor.removeEventFilter(delegate)
        delegate.setModelData(editor, editedModel, editedIndex)
        editor.installEventFilter(delegate)

        childrenView = self.treeWidget.childrenWidget.childrenView
        treeView = self.treeWidget.treeView

        selectedIdxs = childrenView.selectionModel().selectedIndexes()
        if not selectedIdxs:
            selectedIdxs = treeView.selectionModel().selectedIndexes()
            if not selectedIdxs:
                return

        variant = editedModel.data(editedIndex, Qt.UserRole)
        iCurntColumn = editedIndex.column()
        for index in selectedIdxs:

            if (not index.isValid()) or (index.column() != iCurntColumn):
                continue

            if index.flags() & ItemUserFlag.MultiEditable:
                index.model().setData(index, variant)


    def mouseDoubleClickEvent(self, event):

        doubleClickedWdg = self.childAt(event.pos())

        if isinstance(doubleClickedWdg, QtGui.QLabel):

            if event.button() == Qt.LeftButton:

                editedReader = doubleClickedWdg

                readerWidget = editedReader.parent()

                if isinstance(readerWidget, PropertyWidget):

                    mapper = self.mapper

                    index = mapper.indexFromWidget(editedReader)

                    if index.isValid() and (index.flags() & Qt.ItemIsEditable):

                        delegate = self.itemDelegate()
                        editor = delegate.createEditor(readerWidget, QtGui.QStyleOptionViewItem(), index)

                        if editor:

                            layout = readerWidget.layout()
                            layout.addWidget(editor)

                            mapper.addMapping(editor, index.column())
                            editedReader.setVisible(False)

                            editor.installEventFilter(delegate)
                            delegate.setEditorData(editor, index)

                            editor.show()
                            editor.setFocus()

                            if isinstance(editor, QtGui.QComboBox):
                                pressEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress,
                                                                QtCore.QPoint(0, 0),
                                                                Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
                                releaseEvent = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease,
                                                                QtCore.QPoint(0, 0),
                                                                Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)

                                QtGui.qApp.sendEvent(editor, pressEvent)
                                QtGui.qApp.sendEvent(editor, releaseEvent)

                            return

        QtGui.QWidget.mouseDoubleClickEvent(self, event)

    def update(self, *args, **kwargs):
        QtGui.QWidget.update(self, *args, **kwargs)
        self.mapper.setCurrentIndex(self.mapper.currentIndex())

    def resizeImageButton(self, iClampSize):

        iSize = iClampSize - (self.__topMargin + self.__bottomMargin)

        if 64 < iSize < 256:
            self.imageFrame.setMaximumSize(iSize, iSize)
            self.imageFrame.setMinimumSize(iSize, iSize)
            self.imageButton.setIconSize(QtCore.QSize(iSize, iSize))
