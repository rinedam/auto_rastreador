import sys
import threading
import time
import logging
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit, 
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                             QProgressBar, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# Adicione estes imports no topo do arquivo
from PyQt5.QtWidgets import (QTimeEdit, QDialog, QDialogButtonBox, 
                           QListWidget, QListWidgetItem)
from datetime import datetime, time
import json

# Importar o código original
import atualizacao_ssw as ssw_updater

# Configuração de diretórios
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Handler personalizado para capturar logs e enviá-los para a interface
class QTextEditLogger(logging.Handler, QObject):
    log_signal = pyqtSignal(str, int)  # sinal para enviar mensagem e nível de log

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg, record.levelno)

class SSWUpdaterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.schedules = []
        self.initUI()
        self.setupLogging()
        self.setup_schedule_timer()
        
    def initUI(self):
        self.setWindowTitle('Atualizador de Sistema SSW')
        self.setMinimumSize(800, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Título
        title_label = QLabel("Sistema de Atualização SSW")
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        # Informações do aplicativo
        info_label = QLabel("Este aplicativo atualiza o sistema SSW com as localizações dos veículos.")
        info_label.setFont(QFont('Arial', 10))
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # Status
        self.status_label = QLabel("Pronto para iniciar")
        self.status_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminado
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Área de log
        log_label = QLabel("Log de execução:")
        log_label.setFont(QFont('Arial', 10, QFont.Bold))
        main_layout.addWidget(log_label)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont('Consolas', 9))
        self.log_area.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.log_area)
        
        # Botões
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.start_button = QPushButton("Iniciar Atualização")
        self.start_button.setFont(QFont('Arial', 10))
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_update)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Parar")
        self.stop_button.setFont(QFont('Arial', 10))
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_update)
        button_layout.addWidget(self.stop_button)
        
        self.exit_button = QPushButton("Sair")
        self.exit_button.setFont(QFont('Arial', 10))
        self.exit_button.setMinimumHeight(40)
        self.exit_button.clicked.connect(self.close_application)
        button_layout.addWidget(self.exit_button)
        
        # Adicione o botão de configurar horários
        self.schedule_button = QPushButton("Configurar Horários")
        self.schedule_button.setFont(QFont('Arial', 10))
        self.schedule_button.setMinimumHeight(40)
        self.schedule_button.clicked.connect(self.show_schedule_config)
        button_layout.addWidget(self.schedule_button)

        main_layout.addLayout(button_layout)
        
        # Estilizando a interface
        self.apply_style()
        
    def apply_style(self):
        # Estilo geral
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
            }
            QPushButton {
                background-color: #2980b9;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2980b9;
                width: 20px;
            }
        """)
        
        # Botão vermelho para o botão de parar
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        # Botão cinza para o botão de sair
        self.exit_button.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        
        # Botão azul claro para configuração de horários
        self.schedule_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
    def setupLogging(self):
        # Configurar log handler para a interface
        self.log_handler = QTextEditLogger()
        self.log_handler.log_signal.connect(self.update_log)
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOGS_DIR / "atualizacao_ssw_v3.log", encoding='utf-8'),
                self.log_handler
            ]
        )
        
    @pyqtSlot(str, int)
    def update_log(self, message, level):
        # Define cores para os diferentes níveis de log
        color = QColor(0, 0, 0)  # Preto para INFO
        if level >= logging.ERROR:
            color = QColor(255, 0, 0)  # Vermelho para ERROR
        elif level >= logging.WARNING:
            color = QColor(255, 165, 0)  # Laranja para WARNING
        
        self.log_area.setTextColor(color)
        self.log_area.append(message)
        # Rolagem automática para a última linha
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
    
    def start_update(self):
        if self.running:
            return
            
        self.running = True
        self.stop_event.clear()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.exit_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Atualizando o sistema SSW...")
        
        # Função para verificar conexão e executar o processamento em um thread separado
        def update_process():
            try:
                logging.info("Iniciando verificação de conexão...")
                if not ssw_updater.verificar_conexao():
                    logging.error("Falha na conexão à internet. Verifique sua conexão e tente novamente.")
                    self.update_status("Falha na conexão", error=True)
                    return
                
                logging.info("Conexão verificada. Iniciando atualização do sistema...")
                
                # Obter placas e localizações
                logging.info("Consultando placas e localizações via processador_placas.py...")
                try:
                    _, veiculos_com_localizacao = ssw_updater.processador_placas.processar_localizacao_veiculos()
                    
                    if not veiculos_com_localizacao:
                        logging.warning("Nenhum veículo com localização retornado. Encerrando processamento.")
                        self.update_status("Nenhum veículo encontrado", warning=True)
                        return
                    
                    logging.info(f"{len(veiculos_com_localizacao)} veículos com localização obtidos.")
                    
                    # Iterar sobre cada veículo
                    total_veiculos = len(veiculos_com_localizacao)
                    self.update_progress_range(0, total_veiculos)
                    
                    for i, veiculo_info in enumerate(veiculos_com_localizacao):
                        if self.stop_event.is_set():
                            logging.info("Processo interrompido pelo usuário.")
                            break
                            
                        placa = veiculo_info.get('placa')
                        cidade = veiculo_info.get('cidade')
                        estado = veiculo_info.get('estado')
                        
                        if not all([placa, cidade, estado]):
                            logging.warning(f"Veículo {i+1} com dados incompletos. Pulando processamento: {veiculo_info}")
                            continue
                        
                        self.update_status(f"Processando veículo {i+1}/{total_veiculos}: {placa}")
                        self.update_progress_value(i)
                        
                        logging.info(f"Processando veículo {i+1}/{total_veiculos}: "
                                    f"Placa {placa} - {cidade}/{estado}")
                        
                        ssw_updater.atualizar_sistema_para_placa(placa, cidade, estado)
                        
                        if i < total_veiculos - 1 and not self.stop_event.is_set():
                            logging.info("Aguardando intervalo antes do próximo veículo...")
                            time.sleep(5)
                    
                    if not self.stop_event.is_set():
                        logging.info("Todos os veículos foram processados com sucesso!")
                        self.update_status("Processamento concluído", success=True)
                    
                except Exception as e:
                    logging.error(f"Erro ao obter dados de veículos: {e}", exc_info=True)
                    self.update_status("Erro ao obter dados de veículos", error=True)
            
            except Exception as e:
                logging.error(f"Erro não tratado no processo: {e}", exc_info=True)
                self.update_status("Erro não tratado", error=True)
            
            finally:
                if not self.stop_event.is_set():
                    self.stop_event.set()
                self.running_completed()
        
        # Iniciar thread
        self.thread = threading.Thread(target=update_process)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_update(self):
        if not self.running:
            return
            
        self.stop_event.set()
        self.status_label.setText("Parando o processo...")
        logging.info("Solicitação para parar o processo foi recebida.")
        
        # Desabilitar botão de parar para evitar múltiplos cliques
        self.stop_button.setEnabled(False)
    
    def running_completed(self):
        self.running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.exit_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if self.stop_event.is_set():
            if self.status_label.text() != "Processamento concluído":
                self.status_label.setText("Processo interrompido")
    
    def close_application(self):
        if self.running:
            confirm = QMessageBox.question(self, 'Confirmar Saída', 
                                         'Um processo está em execução. Tem certeza que deseja sair?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.stop_event.set()
                # Aguardar um pouco para permitir que o thread termine
                time.sleep(0.5)
                self.close()
        else:
            self.close()
    
    def closeEvent(self, event):
        if self.running:
            confirm = QMessageBox.question(self, 'Confirmar Saída', 
                                         'Um processo está em execução. Tem certeza que deseja sair?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.stop_event.set()
                event.accept()
            else:
                event.ignore()
    
    # Métodos para atualizar a interface a partir de threads
    def update_status(self, message, error=False, warning=False, success=False):
        # Usar QTimer.singleShot para executar no thread da UI
        QTimer.singleShot(0, lambda: self._update_status_ui(message, error, warning, success))
    
    def _update_status_ui(self, message, error=False, warning=False, success=False):
        self.status_label.setText(message)
        
        # Aplicar estilo baseado no tipo de mensagem
        style = "QLabel { font-weight: bold; }"
        if error:
            style += "QLabel { color: #e74c3c; }"
        elif warning:
            style += "QLabel { color: #f39c12; }"
        elif success:
            style += "QLabel { color: #27ae60; }"
        else:
            style += "QLabel { color: #2980b9; }"
            
        self.status_label.setStyleSheet(style)
    
    def update_progress_range(self, minimum, maximum):
        QTimer.singleShot(0, lambda: self._update_progress_range_ui(minimum, maximum))
    
    def _update_progress_range_ui(self, minimum, maximum):
        self.progress_bar.setRange(minimum, maximum)
    
    def update_progress_value(self, value):
        QTimer.singleShot(0, lambda: self._update_progress_value_ui(value))
    
    def _update_progress_value_ui(self, value):
        self.progress_bar.setValue(value)

    def show_schedule_config(self):
        dialog = ScheduleConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.schedules = dialog.get_schedules()
            self.setup_schedule_timer()
            
    def setup_schedule_timer(self):
        # Timer para verificar horários a cada minuto
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_schedule)
        self.schedule_timer.start(60000)  # 60000 ms = 1 minuto
        
    def check_schedule(self):
        current_time = datetime.now().strftime("%H:%M")
        if hasattr(self, 'schedules') and current_time in self.schedules:
            if not self.running:
                logging.info(f"Iniciando atualização agendada: {current_time}")
                self.start_update()

class ScheduleConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configurar Horários')
        self.setMinimumWidth(300)
        self.setup_ui()
        self.load_schedules()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Lista de horários
        self.schedule_list = QListWidget()
        layout.addWidget(QLabel("Horários configurados:"))
        layout.addWidget(self.schedule_list)
        
        # Time picker
        time_layout = QHBoxLayout()
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        add_button = QPushButton("Adicionar")
        add_button.clicked.connect(self.add_time)
        time_layout.addWidget(self.time_edit)
        time_layout.addWidget(add_button)
        layout.addLayout(time_layout)
        
        # Botões de OK/Cancelar
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def add_time(self):
        time_text = self.time_edit.time().toString("HH:mm")
        # Verifica se o horário já existe
        existing_items = [self.schedule_list.item(i).text() 
                         for i in range(self.schedule_list.count())]
        if time_text not in existing_items:
            item = QListWidgetItem(time_text)
            self.schedule_list.addItem(item)
            self.save_schedules()

    def load_schedules(self):
        try:
            with open('schedules.json', 'r') as f:
                schedules = json.load(f)
                for time_str in schedules:
                    self.schedule_list.addItem(QListWidgetItem(time_str))
        except FileNotFoundError:
            pass

    def save_schedules(self):
        schedules = [self.schedule_list.item(i).text() 
                    for i in range(self.schedule_list.count())]
        with open('schedules.json', 'w') as f:
            json.dump(schedules, f)

    def get_schedules(self):
        return [self.schedule_list.item(i).text() 
                for i in range(self.schedule_list.count())]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SSWUpdaterApp()
    window.show()
    sys.exit(app.exec_())