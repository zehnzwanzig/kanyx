"""Qt widgets for optional GitHub update checks, editable due-date calendar, swimlane commands.

No network request happens unless the user clicks Check updates or explicitly opts
in to automatic checks in the Workspace menu.
"""
import calendar
import json
import re
from datetime import date, timedelta
from PySide6.QtCore import Qt, QByteArray, QMimeData, QUrl, QTimer
from PySide6.QtGui import QDrag, QDesktopServices, QColor, QBrush
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QScrollArea, QWidget, QGridLayout,
                               QListWidget, QListWidgetItem, QMessageBox, QInputDialog)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from kanyx_feature_core import due_cards, set_due, add_swimlane, rename_swimlane, move_swimlane, delete_swimlane, set_swimlane_collapsed, swimlanes

# A separate catalogue deliberately avoids modifying the original 13-language
# table lengths relied on by existing localization regression tests.
LANG = {
'en': ['Swimlanes','Show swimlanes','Hide swimlanes','Add swimlane','Manage swimlane','Rename swimlane','Delete swimlane','Move up','Move down','Collapse','Expand','Calendar','Month','Week','Today','All boards','Check for updates…','Check for updates automatically','No updates available','A new Kanyx version is available','Open release page','Your version is up to date','Update check failed','Tasks with due dates','Swimlane name','The default swimlane cannot be deleted','Delete this swimlane? Its cards will be moved to General.'],
'de': ['Swimlanes','Swimlanes anzeigen','Swimlanes ausblenden','Swimlane hinzufügen','Swimlane verwalten','Swimlane umbenennen','Swimlane löschen','Nach oben','Nach unten','Einklappen','Ausklappen','Kalender','Monat','Woche','Heute','Alle Boards','Auf Updates prüfen…','Beim Start automatisch nach Updates suchen','Keine Updates verfügbar','Eine neue Kanyx-Version ist verfügbar','Release-Seite öffnen','Deine Version ist aktuell','Update-Prüfung fehlgeschlagen','Aufgaben mit Fälligkeitsdatum','Name der Swimlane','Die Standard-Swimlane kann nicht gelöscht werden','Swimlane löschen? Ihre Karten werden nach Allgemein verschoben.'],
'es': ['Swimlanes','Mostrar carriles','Ocultar carriles','Añadir carril','Gestionar carril','Renombrar carril','Eliminar carril','Subir','Bajar','Contraer','Expandir','Calendario','Mes','Semana','Hoy','Todos los tableros','Buscar actualizaciones…','Buscar actualizaciones al iniciar','Sin actualizaciones','Hay una nueva versión de Kanyx','Abrir versión','Ya tienes la última versión','Error al buscar actualizaciones','Tareas con vencimiento','Nombre del carril','No se puede eliminar el carril predeterminado','¿Eliminar este carril? Las tarjetas pasarán a General.'],
'fr': ['Couloirs','Afficher les couloirs','Masquer les couloirs','Ajouter un couloir','Gérer le couloir','Renommer le couloir','Supprimer le couloir','Monter','Descendre','Réduire','Développer','Calendrier','Mois','Semaine','Aujourd’hui','Tous les tableaux','Vérifier les mises à jour…','Vérifier au démarrage','Aucune mise à jour','Une nouvelle version de Kanyx est disponible','Ouvrir la version','Vous êtes à jour','Échec de la vérification','Tâches avec échéance','Nom du couloir','Impossible de supprimer le couloir par défaut','Supprimer ce couloir ? Ses cartes iront dans Général.'],
'ja': ['スイムレーン','スイムレーンを表示','スイムレーンを非表示','スイムレーンを追加','スイムレーンを管理','スイムレーン名を変更','スイムレーンを削除','上へ','下へ','折りたたむ','展開','カレンダー','月','週','今日','全ボード','更新を確認…','起動時に更新を確認','更新なし','新しいKanyxがあります','リリースを開く','最新版です','更新確認に失敗','期限付きタスク','スイムレーン名','標準スイムレーンは削除できません','削除しますか？カードは一般へ移動します。'],
'ko': ['스윔레인','스윔레인 표시','스윔레인 숨기기','스윔레인 추가','스윔레인 관리','스윔레인 이름 변경','스윔레인 삭제','위로','아래로','접기','펼치기','달력','월','주','오늘','전체 보드','업데이트 확인…','시작 시 업데이트 확인','업데이트 없음','새 Kanyx 버전이 있습니다','릴리스 열기','최신 버전입니다','업데이트 확인 실패','마감일 있는 작업','스윔레인 이름','기본 스윔레인은 삭제할 수 없습니다','삭제할까요? 카드는 일반으로 이동합니다.'],
'it': ['Swimlane','Mostra swimlane','Nascondi swimlane','Aggiungi swimlane','Gestisci swimlane','Rinomina swimlane','Elimina swimlane','Su','Giù','Comprimi','Espandi','Calendario','Mese','Settimana','Oggi','Tutte le bacheche','Verifica aggiornamenti…','Verifica all’avvio','Nessun aggiornamento','Nuova versione di Kanyx','Apri release','Versione aggiornata','Controllo fallito','Attività con scadenza','Nome swimlane','Non puoi eliminare la swimlane predefinita','Eliminare la swimlane? Le carte passeranno a Generale.'],
'zh_CN': ['泳道','显示泳道','隐藏泳道','添加泳道','管理泳道','重命名泳道','删除泳道','上移','下移','折叠','展开','日历','月','周','今天','所有看板','检查更新…','启动时检查更新','没有更新','有新版本的 Kanyx','打开发布页','已是最新版本','更新检查失败','到期任务','泳道名称','无法删除默认泳道','删除此泳道？卡片将移至常规泳道。'],
'pt_BR': ['Raias','Mostrar raias','Ocultar raias','Adicionar raia','Gerenciar raia','Renomear raia','Excluir raia','Subir','Descer','Recolher','Expandir','Calendário','Mês','Semana','Hoje','Todos os quadros','Verificar atualizações…','Verificar ao iniciar','Nenhuma atualização','Nova versão do Kanyx','Abrir versão','Você está atualizado','Falha na verificação','Tarefas com prazo','Nome da raia','Não é possível excluir a raia padrão','Excluir a raia? Cartões irão para Geral.'],
'pl': ['Swimlane','Pokaż swimlane','Ukryj swimlane','Dodaj swimlane','Zarządzaj swimlane','Zmień nazwę swimlane','Usuń swimlane','W górę','W dół','Zwiń','Rozwiń','Kalendarz','Miesiąc','Tydzień','Dzisiaj','Wszystkie tablice','Sprawdź aktualizacje…','Sprawdzaj przy starcie','Brak aktualizacji','Dostępna nowa wersja Kanyx','Otwórz wydanie','Masz aktualną wersję','Błąd sprawdzania','Zadania z terminem','Nazwa swimlane','Nie można usunąć domyślnej swimlane','Usunąć swimlane? Karty trafią do Ogólne.'],
'ru': ['Дорожки','Показать дорожки','Скрыть дорожки','Добавить дорожку','Управление дорожкой','Переименовать дорожку','Удалить дорожку','Вверх','Вниз','Свернуть','Развернуть','Календарь','Месяц','Неделя','Сегодня','Все доски','Проверить обновления…','Проверять при запуске','Обновлений нет','Доступна новая версия Kanyx','Открыть релиз','У вас последняя версия','Ошибка проверки','Задачи со сроком','Название дорожки','Нельзя удалить основную дорожку','Удалить дорожку? Карточки перейдут в Общие.'],
'hi': ['स्विमलेन','स्विमलेन दिखाएँ','स्विमलेन छिपाएँ','स्विमलेन जोड़ें','स्विमलेन प्रबंधित करें','नाम बदलें','स्विमलेन हटाएँ','ऊपर','नीचे','समेटें','खोलें','कैलेंडर','महीना','सप्ताह','आज','सभी बोर्ड','अपडेट जाँचें…','शुरू होने पर अपडेट जाँचें','कोई अपडेट नहीं','Kanyx का नया संस्करण उपलब्ध है','रिलीज़ खोलें','आपका संस्करण नवीनतम है','अपडेट जाँच विफल','समय-सीमा वाले कार्य','स्विमलेन का नाम','डिफ़ॉल्ट स्विमलेन हटाई नहीं जा सकती','स्विमलेन हटाएँ? कार्ड सामान्य में जाएँगे।'],
'ar': ['مسارات العمل','إظهار المسارات','إخفاء المسارات','إضافة مسار','إدارة المسار','إعادة تسمية المسار','حذف المسار','للأعلى','للأسفل','طي','توسيع','التقويم','شهر','أسبوع','اليوم','كل اللوحات','التحقق من التحديثات…','التحقق عند بدء التشغيل','لا توجد تحديثات','يتوفر إصدار جديد من Kanyx','فتح الإصدار','الإصدار محدث','فشل التحقق','مهام لها موعد','اسم المسار','لا يمكن حذف المسار الافتراضي','حذف المسار؟ ستُنقل البطاقات إلى عام.'],
}
KEYS = LANG['en']
def t(lang,key):
    try: return LANG.get(lang,LANG['en'])[KEYS.index(key)]
    except ValueError: return key

class UpdateChecker:
    def __init__(self, window, version):
        self.window=window
        self.version=version
        self.manager=QNetworkAccessManager(window)
        self.reply=None
        self.manual=False

    def check(self, manual=False):
        if self.reply is not None: return
        self.manual=manual
        req=QNetworkRequest(QUrl('https://api.github.com/repos/zehnzwanzig/kanyx/releases/latest'))
        req.setTransferTimeout(7000)
        req.setRawHeader(b'User-Agent',b'Kanyx-Desktop-UpdateChecker')
        req.setRawHeader(b'Accept',b'application/vnd.github+json')
        self.reply=self.manager.get(req)
        self.reply.finished.connect(self._finished)

    def _finished(self):
        reply=self.reply
        self.reply=None
        if reply is None: return
        try:
            if reply.error()!=QNetworkReply.NetworkError.NoError:
                raise ValueError(reply.errorString())
            data=bytes(reply.readAll())
            if len(data)>1024*1024: raise ValueError('Response too large')
            payload=json.loads(data)
            remote=payload.get('tag_name','')
            if not re.fullmatch(r'v?\d+\.\d+\.\d+', remote): raise ValueError('Invalid release version')
            if not re.fullmatch(r'\d+\.\d+\.\d+', self.version): return
            local_nums=tuple(int(x) for x in self.version.split('.'))
            remote_nums=tuple(int(x) for x in remote.lstrip('v').split('.'))
            if remote_nums>local_nums:
                safe_url=f'https://github.com/zehnzwanzig/kanyx/releases/tag/{remote}'
                message=QMessageBox(self.window)
                message.setWindowTitle('Kanyx')
                message.setText(t(self.window.language,'A new Kanyx version is available')+f': {remote}')
                link=message.addButton(t(self.window.language,'Open release page'),QMessageBox.ButtonRole.AcceptRole)
                message.addButton(self.window.t('Cancel'),QMessageBox.ButtonRole.RejectRole)
                message.exec()
                if message.clickedButton() is link: QDesktopServices.openUrl(QUrl(safe_url))
            elif self.manual:
                QMessageBox.information(self.window,'Kanyx',t(self.window.language,'Your version is up to date'))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            if self.manual:
                QMessageBox.warning(self.window,'Kanyx',t(self.window.language,'Update check failed')+': '+str(exc))
        finally:
            reply.deleteLater()


MIME='application/x-kanyx-calendar-card'
class CalendarDayList(QListWidget):
    def __init__(self,dialog,day):
        super().__init__()
        self.dialog=dialog
        self.day=day
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setMinimumHeight(80)
        self.setStyleSheet('QListWidget{background:#252b35; border:1px solid #3e4655; border-radius:5px; padding:3px;}')
        self.itemDoubleClicked.connect(lambda item:self.dialog.open_card(item.data(Qt.ItemDataRole.UserRole)))

    def startDrag(self,actions):
        item=self.currentItem()
        if item is None: return
        cid=item.data(Qt.ItemDataRole.UserRole)
        drag=QDrag(self)
        mime=QMimeData();mime.setData(MIME,str(cid).encode('ascii'))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self,event):
        if event.mimeData().hasFormat(MIME): event.acceptProposedAction()
        else: event.ignore()
    def dragMoveEvent(self,event):
        if event.mimeData().hasFormat(MIME): event.acceptProposedAction()
        else: event.ignore()
    def dropEvent(self,event):
        if not event.mimeData().hasFormat(MIME): event.ignore();return
        try: cid=int(bytes(event.mimeData().data(MIME)).decode('ascii'))
        except ValueError: event.ignore();return
        try: set_due(self.dialog.window.store,cid,self.day.isoformat())
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self,'Kanyx',str(exc));event.ignore();return
        event.acceptProposedAction()
        self.dialog.window.refresh()
        QTimer.singleShot(0,self.dialog.populate)

class DueDateCalendarDialog(QDialog):
    def __init__(self,window):
        super().__init__(window)
        self.window=window
        self.anchor=date.today()
        self.setWindowTitle(t(window.language,'Calendar'))
        self.resize(1050,740)
        root=QVBoxLayout(self)
        tools=QHBoxLayout()
        self.board=QComboBox()
        self.board.addItem(t(window.language,'All boards'),None)
        for b in window.store.rows('SELECT id,title FROM boards ORDER BY position,id'):
            self.board.addItem(b['title'],b['id'])
        self.board.currentIndexChanged.connect(self.populate)
        tools.addWidget(self.board)
        self.mode=QComboBox()
        for code in ('Month','Week'):
            self.mode.addItem(t(window.language,code),code)
        self.mode.currentIndexChanged.connect(self.populate)
        tools.addWidget(self.mode)
        for text, callback in [('‹',lambda:self.shift(-1)),(t(window.language,'Today'),self.today),('›',lambda:self.shift(1))]:
            b=QPushButton(text);b.clicked.connect(callback);tools.addWidget(b)
        self.title=QLabel()
        tools.addWidget(self.title,1)
        root.addLayout(tools)
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll,1)
        self.populate()

    def today(self):
        self.anchor=date.today();self.populate()
    def shift(self,n):
        if self.mode.currentData()=='Week':
            self.anchor+=timedelta(days=n*7)
        else:
            m=self.anchor.month+n; y=self.anchor.year+(m-1)//12
            m=(m-1)%12+1
            self.anchor=date(max(1,min(9999,y)),m,1)
        self.populate()
    def open_card(self,cid):
        self.window.edit_card(cid)
        self.populate()

    def populate(self,*args):
        selected=self.board.currentData()
        cards=due_cards(self.window.store,selected)
        by_day={}
        for c in cards:
            by_day.setdefault(c['due'],[]).append(c)
        if self.mode.currentData()=='Week':
            monday=self.anchor-timedelta(days=self.anchor.weekday())
            weeks=[[monday+timedelta(days=i) for i in range(7)]]
        else:
            weeks=calendar.Calendar(firstweekday=0).monthdatescalendar(self.anchor.year,self.anchor.month)
        self.title.setText(self.anchor.strftime('%B %Y') if self.mode.currentData()=='Month' else f'{weeks[0][0]} — {weeks[0][-1]}')
        body=QWidget()
        grid=QGridLayout(body)
        grid.setSpacing(7)
        today=date.today()
        for dayindex,name in enumerate(('Mon','Tue','Wed','Thu','Fri','Sat','Sun')):
            label=QLabel(name);label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(label,0,dayindex)
        for w,row in enumerate(weeks):
            for d,day in enumerate(row):
                cell=QWidget(); col=QVBoxLayout(cell);col.setContentsMargins(3,3,3,3);col.setSpacing(3)
                label=QLabel(day.strftime('%d %b'))
                label.setStyleSheet('font-weight:bold;color:'+('#e8bc73' if day==today else '#b5becf' if day.month!=self.anchor.month and self.mode.currentData()=='Month' else '#ffffff')+';')
                col.addWidget(label)
                tasks=CalendarDayList(self,day)
                for card in by_day.get(day.isoformat(),[]):
                    name=card['title']
                    if selected is None: name=f"{card['board_title']}: {name}"
                    item=QListWidgetItem(name);item.setData(Qt.ItemDataRole.UserRole,card['id'])
                    if day<today: item.setForeground(QBrush(QColor('#ff8989')))
                    tasks.addItem(item)
                col.addWidget(tasks,1)
                grid.addWidget(cell,w+1,d)
            grid.setRowStretch(w+1,1)
        old=self.scroll.takeWidget()
        self.scroll.setWidget(body)
        if old is not None:old.deleteLater()


def manage_swimlane(window,sid):
    sl=window.store.one('SELECT * FROM swimlanes WHERE id=?',(sid,))
    if not sl:return
    lang=window.language
    keys=['Rename swimlane','Move up','Move down','Collapse' if not sl['collapsed'] else 'Expand','Delete swimlane']
    opts=[t(lang,x) for x in keys]
    selected,ok=QInputDialog.getItem(window,t(lang,'Manage swimlane'),t(lang,'Manage swimlane'),opts,0,False)
    if not ok:return
    action=keys[opts.index(selected)]
    try:
        if action=='Rename swimlane':
            title,accepted=QInputDialog.getText(window,t(lang,'Rename swimlane'),t(lang,'Swimlane name'),text=sl['title'])
            if accepted and title.strip():rename_swimlane(window.store,sid,title)
        elif action in ('Move up','Move down'):
            all_rows=swimlanes(window.store,sl['board_id'])
            old=next(i for i,row in enumerate(all_rows) if row['id']==sid)
            move_swimlane(window.store,sid,old+(-1 if action=='Move up' else 1))
        elif action in ('Collapse','Expand'):
            set_swimlane_collapsed(window.store,sid,not sl['collapsed'])
        elif action=='Delete swimlane':
            if sl['is_default']:
                QMessageBox.information(window,'Kanyx',t(lang,'The default swimlane cannot be deleted'));return
            if QMessageBox.question(window,t(lang,'Delete swimlane'),t(lang,'Delete this swimlane? Its cards will be moved to General.'))==QMessageBox.StandardButton.Yes:
                delete_swimlane(window.store,sid)
    except (ValueError, OSError) as exc:
        QMessageBox.warning(window,'Kanyx',str(exc))
    window.refresh()
